"""Registro explícito de fuentes; no se rastrea la web abierta ni plataformas privadas."""
import asyncio
import http.client
import ipaddress
import json
import re
import socket
import ssl
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from itertools import zip_longest
import hashlib
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from xml.etree import ElementTree


@dataclass(frozen=True)
class Feed:
    url: str
    host: str
    organization: str
    language: str = 'en'
    kind: str = 'rss'
    article_host: str | None = None


FEEDS = (
    Feed('https://openai.com/news/rss.xml', 'openai.com', 'openai'),
    Feed('https://huggingface.co/blog/feed.xml', 'huggingface.co', 'huggingface'),
    Feed('https://blog.google/technology/ai/rss/', 'blog.google', 'google'),
    Feed('https://www.microsoft.com/en-us/research/feed/', 'www.microsoft.com', 'microsoft'),
    Feed('https://blogs.nvidia.com/feed/', 'blogs.nvidia.com', 'nvidia'),
    Feed('https://deepmind.google/blog/rss.xml','deepmind.google','google'),
    Feed('https://www.anthropic.com/news','www.anthropic.com','anthropic',kind='html'),
    Feed('https://ai.meta.com/blog/','ai.meta.com','meta',kind='html'),
    Feed('https://rss.arxiv.org/rss/cs.AI','rss.arxiv.org','unverified_scientific_authors',article_host='arxiv.org'),
)
DOCUMENT_HOSTS = {'docs.python.org':'python', 'fastapi.tiangolo.com':'fastapi', 'pydantic.dev':'pydantic',
                  'docs.pydantic.dev':'pydantic', 'developers.openai.com':'openai', 'ai.google.dev':'google',
                  'platform.claude.com':'anthropic', 'docs.anthropic.com':'anthropic',
                  # Gemini docs now redirect from ai.google.dev (comprobado 04/11/2026).
                  'aistudio.google.com':'google',
                  # SQL semantics used by the verified sqlite example (INSERT OR REPLACE, PRIMARY KEY).
                  'www.sqlite.org':'sqlite',
                  # Official consumer help centres (Herramientas). Fetched with the production fetcher on
                  # 11/11/2026: HTTP 200 and >3,800 chars. help.openai.com answers 403 and is not listed.
                  'support.google.com':'google', 'support.claude.com':'anthropic'}
RAPID_FEEDS=(Feed('https://www.tesla.com/blog','www.tesla.com','tesla',kind='html'),
    Feed('https://waymo.com/blog/','waymo.com','google',kind='html'),
    Feed('https://ir.tesla.com/press','ir.tesla.com','tesla',kind='html'),
    Feed('https://nvidianews.nvidia.com/releases.xml','nvidianews.nvidia.com','nvidia'))
INDEPENDENT_FEEDS=(Feed('https://techcrunch.com/category/artificial-intelligence/feed/','techcrunch.com','techcrunch'),
    Feed('https://feeds.bbci.co.uk/news/technology/rss.xml','feeds.bbci.co.uk','bbc',article_host='www.bbc.com'))
# Explicit publisher identities, not arbitrary domains suggested by a model.
NEWS_HOSTS = {'x.ai':'xai','www.x.ai':'xai','api-docs.deepseek.com':'deepseek',
    'www.deepseek.com':'deepseek','www.reuters.com':'reuters','apnews.com':'ap',
    'techcrunch.com':'techcrunch','arstechnica.com':'arstechnica','www.theverge.com':'vox',
    'www.engadget.com':'engadget','research.google':'google','blog.google':'google',
    'www.nvidia.com':'nvidia','nvidianews.nvidia.com':'nvidia','news.microsoft.com':'microsoft',
    'blogs.microsoft.com':'microsoft','about.fb.com':'meta','www.anthropic.com':'anthropic',
    'www.bbc.com':'bbc','www.bbc.co.uk':'bbc','claude.com':'anthropic','research.meta.ai':'meta',
    'cloud.google.com':'google','www.axios.com':'axios','www.tomshardware.com':'tomshardware',
    'www.pymnts.com':'pymnts','www.oracle.com':'oracle','blogs.oracle.com':'oracle'}
NEWS_HOSTS.update({'www.sec.gov':'sec_filing_host','sec.gov':'sec_filing_host',
    'devblogs.microsoft.com':'microsoft','docs.x.ai':'xai',
    'ir.amd.com':'amd','newsroom.amd.com':'amd','help.openai.com':'openai'})
# Confirmed against the registrant's filed cover, not the search model's label.
SEC_REGISTRANTS={'2130357':('anthropic',r'Anthropic,?\s+PBC')}
HOSTS = frozenset(f.host for f in (*FEEDS,*RAPID_FEEDS,*INDEPENDENT_FEEDS)) | {f.article_host for f in (*FEEDS,*INDEPENDENT_FEEDS) if f.article_host} | DOCUMENT_HOSTS.keys() | NEWS_HOSTS.keys()
MAX_BYTES = 2_000_000
MAX_CANDIDATE_FETCHES = 12
# Curated namespaces, confirmed against HF organization metadata on 24/10/2026.
# Unknown namespaces never become independent organizations just from their URL.
HF_ORGANIZATIONS = {
    'microsoft': ('microsoft', '5e6485f787403103f9f1055e'),
    'allenai': ('ai2', '5e70f3648ce3c604d78fe132'),
}


class SourceError(Exception):
    def __init__(self, message, code='source_error', http_status=None,retry_after=None):
        super().__init__(message)
        self.code, self.http_status = code, http_status
        self.retry_after=retry_after


def canonical(url: str):
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or p.username or p.password or p.port not in (None,443):
            raise SourceError('Destino no permitido','unsafe_url')
        if p.hostname not in HOSTS:raise SourceError('Dominio no autorizado','domain_not_allowed')
    except ValueError:raise SourceError('URL no válida','unsafe_url') from None
    if len(url) > 2000 or any(ord(c) < 33 for c in url) or '\\' in url:
        raise SourceError('URL inválida','unsafe_url')
    if p.hostname in {'sec.gov','www.sec.gov'} and not re.fullmatch(r'/Archives/edgar/data/\d{1,10}/\d{18}/[a-zA-Z0-9_.-]+\.html?',p.path):
        raise SourceError('Ruta SEC no autorizada','official_path_not_allowed')
    query=[]
    try:fields=parse_qsl(p.query,keep_blank_values=True,max_num_fields=30)
    except ValueError:raise SourceError('Demasiados parámetros','unsafe_url') from None
    for key,value in fields:
        if key=='page' and is_news_index(url) and re.fullmatch(r'[1-9]\d{0,2}',value):query.append((key,value))
    return urlunsplit(('https',p.hostname,p.path or '/',urlencode(query),''))


def public_addresses(host):
    addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise SourceError('DNS no público')
    return addresses


def fetch(url: str, max_bytes=MAX_BYTES):
    """DNS validado y fijado al socket real; TLS verifica el nombre original."""
    for _ in range(4):
        url = canonical(url)
        p = urlsplit(url)
        addresses = public_addresses(p.hostname)
        conn = http.client.HTTPSConnection(p.hostname, timeout=12, context=ssl.create_default_context())
        # HTTPSConnection aplica SNI/verificación contra conn.host, no contra la IP.
        conn._create_connection = lambda address, timeout, source_address=None: socket.create_connection((addresses[0], 443), timeout, source_address)
        try:
            target=(p.path or '/')+('?' + p.query if p.query else '')
            conn.request('GET', target, headers={'User-Agent': 'ForoIAResearch/1.0 (+https://foroiaaldia.com; admin@foroiaaldia.com)', 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                url = canonical(urljoin(url, response.getheader('Location', '')))
                continue
            if response.status != 200:
                raise SourceError('Fuente no accesible', 'http_status', response.status,response.getheader('Retry-After'))
            encoding=response.getheader('Content-Encoding','identity').strip().lower()
            if encoding not in {'identity','gzip'}:
                raise SourceError('Compresión no admitida', 'unsupported_encoding')
            content_type = response.getheader('Content-Type', '').split(';')[0].lower()
            formats={'text/html', 'text/xml', 'application/xml', 'application/rss+xml', 'application/atom+xml'}
            if p.hostname in DOCUMENT_HOSTS:formats|={'text/plain','text/markdown'}
            if content_type not in formats:
                raise SourceError('Formato no permitido', 'unsupported_format')
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise SourceError('Fuente demasiado grande', 'source_too_large')
            if encoding=='gzip':
                try:
                    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
                    body=decoder.decompress(body,max_bytes+1)
                    if len(body)>max_bytes or decoder.unconsumed_tail:
                        raise SourceError('Fuente descomprimida demasiado grande','source_too_large')
                    if not decoder.eof or decoder.unused_data:
                        raise SourceError('Compresión no válida','invalid_compression')
                except zlib.error:
                    raise SourceError('Compresión no válida','invalid_compression') from None
            return url, body
        finally:
            conn.close()
    raise SourceError('Demasiadas redirecciones', 'redirect_limit')


class HFByline(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.organizations = set()
        self.staff = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        raw = values.get('data-props', '')
        if values.get('data-target') != 'BlogAuthorsByline' or not isinstance(raw, str) or len(raw) > 64_000:
            return
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('authors'), list):
                return
            for row in data['authors'][:100]:
                author = row.get('author') if isinstance(row, dict) else None
                if isinstance(author, dict) and author.get('isHf') is True:
                    self.staff = True
                org = row.get('org') if isinstance(row, dict) else None
                if isinstance(org, dict) and org.get('type') == 'org':
                    self.organizations.add((str(org.get('name')), str(org.get('_id'))))
        except (ValueError, TypeError, RecursionError):
            return


def source_attribution(url, body, fallback):
    from app.research.selection import PUBLISHERS
    path = urlsplit(url)
    parts = path.path.strip('/').split('/')
    actual = PUBLISHERS.get(path.hostname) or NEWS_HOSTS.get(path.hostname)
    result = {'organization': actual or fallback, 'organization_verified': actual is not None, 'platform': path.hostname}
    if path.hostname in {'sec.gov','www.sec.gov'}:
        issuer=sec_issuer(url,plain(body))
        return dict(organization=issuer or 'unverified_sec_registrant',organization_verified=bool(issuer),
            platform=path.hostname,authorship_role='issuer_filing')
    if path.hostname != 'huggingface.co' or parts[0] != 'blog':
        return result
    byline = HFByline()
    byline.feed(body.decode('utf-8', errors='replace'))
    if len(parts) == 2 and byline.staff:
        result['organization_verified'] = True
    if len(parts) == 3:
        known = HF_ORGANIZATIONS.get(parts[1])
        if known and (parts[1], known[1]) in byline.organizations:
            result.update(organization=known[0], organization_verified=True)
    return result


def sec_issuer(url,text):
    p=urlsplit(url);match=re.match(r'/Archives/edgar/data/(\d+)/',p.path)
    known=SEC_REGISTRANTS.get(match[1]) if match else None
    if p.hostname not in {'sec.gov','www.sec.gov'} or not known:return None
    cover=text[:12000]
    return known[0] if re.search(known[1],cover,re.I) and re.search(r'Exact name of registrant',cover,re.I) else None


def content_origin(url, body):
    """Explicit cross-publication canonical only; no request follows this value."""
    class Origin(HTMLParser):
        value = None
        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == 'link' and 'canonical' in values.get('rel', '').lower().split():
                try: self.value = canonical(urljoin(url, values.get('href', '')))
                except (ValueError, SourceError): pass
    parser = Origin(); parser.feed(body.decode('utf-8', errors='replace'))
    return parser.value or url


def independent_organizations(evidence):
    # Old expedients have no verification flag and retain their original grouping.
    return {s['organization'] for s in evidence if s.get('organization_verified', True) is True}


def failure_details(url, stage, exc):
    # Controlled codes and canonical public URLs, never provider text or response bodies.
    if isinstance(exc, SourceError):
        code = exc.code
    elif isinstance(exc, ssl.SSLError):
        code = 'tls_error'
    elif isinstance(exc, TimeoutError):
        code = 'timeout'
    elif isinstance(exc, ElementTree.ParseError):
        code = 'invalid_feed'
    else:
        code = 'network_error' if isinstance(exc, OSError) else 'invalid_response'
    detail = {'url': url, 'stage': stage, 'code': code}
    if isinstance(exc, SourceError) and exc.http_status is not None:
        detail['http_status'] = exc.http_status
    return detail


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'aside'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'aside'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(body: bytes, max_chars=18_000):
    parser = Text()
    parser.feed(body.decode('utf-8', errors='replace'))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()[:max_chars]


def article_plain(body):
    html=body.decode('utf-8',errors='replace')
    class Body(HTMLParser):
        def __init__(self):super().__init__();self.depth=0;self.parts=[];self.blocks=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if not self.depth and tag=='div' and ('article-body' in a.get('class','').split() or a.get('itemprop')=='articleBody'):
                self.depth=1;self.parts=[];return
            if self.depth:
                if tag=='div':self.depth+=1
                self.parts.append(self.get_starttag_text())
        def handle_endtag(self,tag):
            if self.depth:
                if tag=='div':self.depth-=1
                if not self.depth:self.blocks.append(''.join(self.parts));return
                self.parts.append('</'+tag+'>')
        def handle_data(self,data):
            if self.depth:self.parts.append(data)
    parser=Body();parser.feed(html)
    explicit=[plain(b.encode()) for b in parser.blocks]
    if explicit:return max(explicit,key=len)
    blocks=[plain(b.encode()) for tag in ('article','main') for b in re.findall(r'<'+tag+r'\b[^>]*>(.*?)</'+tag+'>',html,re.I|re.S)]
    substantial=[b for b in blocks if len(b)>=500]
    return max(substantial,key=len) if substantial else plain(body)


def sec_title(url,text):
    org=sec_issuer(url,text)
    form=re.search(r'\bFORM\s+(S[- ]1|10[- ]K|10[- ]Q|8[- ]K)\b',text[:4000],re.I)
    return ('Anthropic, PBC — Form '+form[1]) if org=='anthropic' and form else ''


def is_news_index(url,body=None):
    p=urlsplit(url);path=p.path.rstrip('/')
    if p.hostname in {'sec.gov','www.sec.gov'}:return bool(re.search(r'-index\.html?$',path))
    if path in {'','/news','/blog','/newsroom','/news/latest','/news/announcements','/news/company-announcements',
        '/resources/product-announcements','/newsroom/anthropic','/en/news','/company','/foundry','/developers/release-notes',
        '/all-news','/news-events/press-releases'}:return True
    if body:
        title=page_title(body).strip().lower()
        if title in {'news','latest news','newsroom','company announcements','noticias','comunicados'}:return True
        if re.search(br'"@type"\s*:\s*"CollectionPage"',body):return True
    return False


def news_links(body,base_url,same_organization=False):
    """Bounded publisher links, not evidence; keep editorial text outside nav/footer."""
    from app.research.selection import PUBLISHERS
    registry={**PUBLISHERS,**NEWS_HOSTS};base_org=registry.get(urlsplit(base_url).hostname)
    class Links(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.hidden=0;self.current=None;self.rows={}
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag in {'nav','footer','header','script','style','noscript','aside'}:self.hidden+=1
            if tag=='a':
                self.current=None
                if self.hidden or len(self.rows)>=200:return
                try:
                    url=canonical(urljoin(base_url,a.get('href','')));parts=urlsplit(url)
                    if same_organization and registry.get(parts.hostname)!=base_org:return
                    if is_news_index(url) or not (parts.path.startswith(('/news/','/blog/','/index/','/resources/','/article/','/articles/','/company-news/','/technology/','/products/','/en-us/','/foundry/','/Archives/edgar/data/','/news-events/press-releases/detail/','/en/articles/')) or re.match(r'/20\d\d/\d\d/',parts.path)):return
                    if parts.path.lower().endswith(('.pdf','.zip','.xml','.jpg','.png')):return
                    self.current={'url':url,'parts':[]}
                except (ValueError,SourceError):return
        def handle_data(self,data):
            if self.current and not self.hidden:self.current['parts'].append(data)
        def handle_endtag(self,tag):
            if tag in {'nav','footer','header','script','style','noscript','aside'}:self.hidden=max(0,self.hidden-1)
            if tag=='a' and self.current:
                title=' '.join(' '.join(self.current['parts']).split())[:300];url=self.current['url']
                minimum=2 if urlsplit(url).hostname in {'sec.gov','www.sec.gov'} else 12
                if len(title)>=minimum and len(title)>len(self.rows.get(url,{}).get('title','')):
                    stamp=None
                    match=re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s*(20\d\d)\b',title)
                    if match:
                        months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
                        try:stamp=datetime(int(match[3]),months.index(match[1][:3].lower())+1,int(match[2]),tzinfo=UTC).isoformat()
                        except ValueError:pass
                    self.rows[url]={'url':url,'title':title,'published':stamp}
                self.current=None
    parser=Links();parser.feed(body.decode('utf-8',errors='replace'))
    return list(parser.rows.values())[:100]


def publication_stamp(body,url=None):
    """Prefer explicit original publication metadata; never dateModified."""
    html=body.decode('utf-8',errors='replace')
    if url and urlsplit(url).hostname=='ir.amd.com':
        # The IR publisher marks the original release explicitly. A naive
        # datetime alone is insufficient: verify the displayed timezone too.
        released=re.search(r'<p\b[^>]*class=["\'][^"\']*\bspr-ir-news-article-date\b[^"\']*["\'][^>]*>Released ([A-Za-z]+ \d{1,2}, 20\d\d)</p>',html)
        visible=re.search(r'<time\b[^>]*class=["\']date["\'][^>]*>\s*([A-Za-z]+ \d{1,2}, 20\d\d \d{1,2}:\d{2} [ap]m) (EDT|EST)\s*</time>',html)
        if released and visible:
            try:
                from zoneinfo import ZoneInfo
                local=datetime.strptime(visible[1],'%B %d, %Y %I:%M %p').replace(tzinfo=ZoneInfo('America/New_York'))
                if local.strftime('%B %d, %Y')==datetime.strptime(released[1],'%B %d, %Y').strftime('%B %d, %Y') and local.tzname()==visible[2]:
                    return local.astimezone(UTC),'instant'
            except ValueError:pass
    values=re.findall(r'"datePublished"\s*:\s*"([^"\n]{10,40})"',html)[:4]
    class Dates(HTMLParser):
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='meta' and (a.get('property') in {'article:published_time','og:published_time'} or
                a.get('itemprop')=='datePublished' or a.get('name') in {'datePublished','pubdate','publish_date'}):
                values.append(a.get('content',''))
    Dates().feed(body.decode('utf-8',errors='replace'))
    # Explicit visible publication label; exclude sidebar dates and copyright.
    visible=re.search(r'<div\b[^>]*class=["\'][^"\']*\barticle-date\b[^"\']*["\'][^>]*>\s*([A-Za-z]+ \d{1,2}, 20\d\d)\s*</div>',body.decode('utf-8',errors='replace'))
    if visible:
        try:
            values.append(datetime.strptime(visible[1],'%B %d, %Y').date().isoformat())
        except ValueError:
            pass
    if url and urlsplit(url).hostname in {'sec.gov','www.sec.gov'}:
        cover=plain(body)[:4000]
        filed=re.search(r'As filed with the Securities and Exchange Commission on ([A-Za-z]+ \d{1,2}, 20\d\d)',cover,re.I)
        if filed:
            try:return datetime.strptime(filed[1],'%B %d, %Y').replace(tzinfo=UTC),'sec_filing_calendar_day'
            except ValueError:pass
    for raw in values:
        try:
            stamp=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if stamp.tzinfo:return stamp.astimezone(UTC),'instant'
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):return stamp.replace(tzinfo=UTC),'calendar_day'
        except ValueError:pass
    return None,'unverified'


def page_title(body):
    class Title(HTMLParser):
        def __init__(self):super().__init__();self.active=False;self.parts=[]
        def handle_starttag(self,tag,attrs):
            if tag=='h1' and not self.parts:self.active=True
        def handle_endtag(self,tag):
            if tag=='h1':self.active=False
        def handle_data(self,data):
            if self.active:self.parts.append(data)
    parser=Title();parser.feed(body.decode('utf-8',errors='replace'))
    return ' '.join(' '.join(parser.parts).split())[:200]


def article_date(body):
    class Dates(HTMLParser):
        dates=[]
        def __init__(self):super().__init__();self.dates=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='meta' and a.get('property') in {'article:published_time','og:published_time'}:self.dates.append(a.get('content',''))
            if tag=='time':self.dates.append(a.get('datetime',''))
    parser=Dates();parser.feed(body.decode('utf-8',errors='replace'))
    html=body.decode('utf-8',errors='replace')
    parser.dates=re.findall(r'"datePublished"\s*:\s*"([^"\n]{10,40})"',html)[:4]+parser.dates
    for raw in parser.dates:
        try:
            value=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if value.tzinfo:return value.astimezone(UTC)
        except ValueError:pass
    return None


def parse_news_index(body,feed):
    class Links(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.rows=[];self.current=None
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a':
                self.current=None
                try:
                    url=canonical(urljoin(feed.url,a.get('href','')))
                    if urlsplit(url).hostname==feed.host and urlsplit(url).path.startswith(('/news/','/blog/','/press-release/')):
                        self.current={'url':url,'parts':[]}
                except (ValueError,SourceError):pass
        def handle_data(self,data):
            if self.current:self.current['parts'].append(data)
        def handle_endtag(self,tag):
            if tag=='a' and self.current:
                title=' '.join(self.current['parts']).strip()[:200]
                if len(title)>=12:self.rows.append({'url':self.current['url'],'title':title,'published':None,
                    'organization':feed.organization,'language':feed.language})
                self.current=None
    parser=Links();parser.feed(body.decode('utf-8',errors='replace'))
    return list({row['url']:row for row in parser.rows}.values())[:20]


def parse_feed(body: bytes, feed: Feed, now: datetime, max_age_hours=48):
    if b'\x00' in body or re.search(br'<!\s*(?:DOCTYPE|ENTITY)', body, re.I):
        raise SourceError('XML no permitido')
    root = ElementTree.fromstring(body)
    rows = []
    for item in root.findall('.//item')[:60]:
        try:
            raw_date=item.findtext('pubDate','') or item.findtext('{http://purl.org/dc/elements/1.1/}date','')
            try:published = parsedate_to_datetime(raw_date)
            except (ValueError,TypeError):published=datetime.fromisoformat(raw_date.replace('Z','+00:00'))
            if published.tzinfo is None:
                continue
            published = published.astimezone(UTC)
            if not now - timedelta(hours=max_age_hours) <= published <= now + timedelta(minutes=5):
                continue
            url = canonical(item.findtext('link', '').strip())
            if urlsplit(url).hostname != (feed.article_host or feed.host):
                continue
            title = plain((item.findtext('title', '')).encode())[:200]
            # Only explicit full-content RSS, never expand a short description into facts.
            full_content = item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded', '')
            row = {'url': url, 'title': title, 'published': published.isoformat(), 'organization': feed.organization, 'language': feed.language}
            if full_content:
                row.update(rss_text=plain(full_content.encode()), feed_url=feed.url)
            rows.append(row)
        except (ValueError, TypeError, SourceError, OverflowError):
            continue
    return rows


async def collect(now, existing_urls, initial_document_limit=8):
    if not 1 <= initial_document_limit <= 8:
        raise ValueError('document limit outside bounds')
    rows, failures, details, recoveries = {}, 0, [], []
    for feed in FEEDS:
        try:
            _, raw = await asyncio.to_thread(fetch, feed.url, 2_000_000)
            for row in (parse_news_index(raw,feed) if feed.kind=='html' else parse_feed(raw, feed, now)):
                if row['url'].rstrip('/') not in existing_urls:
                    rows[row['url']] = row
        except (OSError, ValueError, SourceError, ElementTree.ParseError, http.client.HTTPException) as exc:
            failures += 1
            details.append(failure_details(feed.url, 'feed', exc))
    # Novedad y utilidad aproximadas; no se presenta como medición de popularidad global.
    keywords = re.compile(r'\b(model|open|release|agent|code|developer|research|launch|AI)\b', re.I)
    ordered = sorted(rows.values(), key=lambda r: (len(keywords.findall(r['title'])), r.get('published') or ''), reverse=True)
    groups = {}
    for row in ordered:
        groups.setdefault(row['organization'], []).append(row)
    ordered = [row for batch in zip_longest(*groups.values()) for row in batch if row is not None]
    evidence, attempted = [], []
    for row in ordered[:MAX_CANDIDATE_FETCHES]:
        if len(evidence) >= initial_document_limit:
            break
        attempted.append(row['url'])
        try:
            final, raw = await asyncio.to_thread(fetch, row['url'])
            if row.get('published') is None:
                stamp=article_date(raw)
                if stamp is None or not now-timedelta(hours=48)<=stamp<=now+timedelta(minutes=5):
                    raise SourceError('Fecha no verificable o noticia antigua','unverified_or_stale_date')
                row=dict(row,published=stamp.isoformat())
            text = plain(raw)
            if len(text) < 500 or final in {r['url'] for r in evidence}:
                continue
            # Confirm the organization against both the curated namespace and byline.
            # Hosting platform is not evidence that the authors belong to that company.
            attribution = source_attribution(final, raw, row['organization'])
            # URL-derived IDs survive changes in feed order; exact content gets its own hash.
            identifier = int(hashlib.sha256(final.encode()).hexdigest()[:12], 16)
            evidence.append({**{k: v for k, v in row.items() if k != 'rss_text'}, 'id': identifier,
                'url': final, 'text': text, 'content_origin': content_origin(final, raw), 'retrieval_method': 'page', **attribution})
        except (OSError, ValueError, SourceError, http.client.HTTPException) as exc:
            failures += 1
            details.append(failure_details(row['url'], 'article', exc))
            if isinstance(exc, SourceError) and exc.http_status == 403 and len(row.get('rss_text', '')) >= 500:
                # A publisher's already fetched full-content feed is a separate permitted
                # representation, not a proxy/retry of the blocked page. HF byline remains unverified.
                attribution = source_attribution(row['url'], b'', row['organization'])
                identifier = int(hashlib.sha256(row['url'].encode()).hexdigest()[:12], 16)
                evidence.append({**{k: v for k, v in row.items() if k != 'rss_text'}, 'id': identifier,
                    'text': row['rss_text'], 'retrieval_method': 'rss_full_content', **attribution})
                recoveries.append({'url': row['url'], 'method': 'rss_full_content', 'feed_url': row['feed_url']})
    return evidence, {'feed_count': len(FEEDS), 'candidate_count': len(rows), 'fetch_failures': failures,
        'fetch_errors': details, 'recoveries': recoveries, 'source_organizations': sorted(independent_organizations(evidence)),
        'fetch_attempts': len(attempted), 'attempted_urls': attempted,
        'unfetched_candidates': [row for row in ordered[:MAX_CANDIDATE_FETCHES] if row['url'] not in attempted]}


async def recover_related(evidence, stats):
    """Unused authorized RSS entries, related first then next topic; shared limits."""
    from app.research.selection import relationship, select
    result = list(evidence)
    attempted = set(stats.get('attempted_urls', []))
    remaining = max(0, MAX_CANDIDATE_FETCHES - stats.get('fetch_attempts', MAX_CANDIDATE_FETCHES))
    log = []
    pending = stats.get('unfetched_candidates', [])[:MAX_CANDIDATE_FETCHES]
    pending = sorted(pending, key=lambda row: not any(relationship(row,s)['related'] for s in result))
    for row in pending:
        if not remaining or len(result) >= 8:
            break
        if row['url'] in attempted:
            continue
        related = any(relationship(row,s)['related'] for s in result)
        remaining -= 1; attempted.add(row['url'])
        stats['fetch_attempts'] = stats.get('fetch_attempts', 0) + 1
        try:
            final, raw = await asyncio.to_thread(fetch, row['url'])
            if row.get('published') is None:
                now=datetime.now(UTC);stamp=article_date(raw)
                if stamp is None or not now-timedelta(hours=48)<=stamp<=now+timedelta(minutes=5):
                    raise SourceError('Fecha no verificable o noticia antigua','unverified_or_stale_date')
                row=dict(row,published=stamp.isoformat())
            text = plain(raw)
            if len(text) < 500 or final in {s['url'] for s in result}:
                log.append({'url': row['url'], 'reason': 'short_or_duplicate_document'}); continue
            source = {**{k:v for k,v in row.items() if k!='rss_text'}, 'url':final,
                'id':int(hashlib.sha256(final.encode()).hexdigest()[:12],16), 'text':text,
                'retrieval_method':'related_page', 'content_origin':content_origin(final,raw),
                **source_attribution(final, raw, row['organization'])}
            result.append(source)
            log.append({'url':final,'reason':'recovered_related_document' if related else 'recovered_next_topic_document'})
            if select(result)[0]: break
        except (OSError, ValueError, SourceError, http.client.HTTPException) as exc:
            stats['fetch_failures'] = stats.get('fetch_failures',0)+1
            stats['fetch_errors'] = [*stats.get('fetch_errors',[]), failure_details(row['url'],'related_article',exc)]
            log.append({'url':row['url'],'reason':'related_fetch_failed'})
    stats['attempted_urls'] = sorted(attempted)
    stats['related_recovery'] = {'attempts':log,'reason':'completed' if log else 'no_unused_related_entries_or_bounds_exhausted'}
    return result, stats


async def restore(metadata, now, required_ids=None):
    """Volver a consultar las mismas evidencias para una revisión aplazada."""
    if required_ids is not None:
        if not required_ids or not set(required_ids) <= {s['id'] for s in metadata}:
            raise SourceError('Faltan fuentes citadas')
        metadata = [s for s in metadata if s['id'] in required_ids]
    if not 2 <= len(metadata) <= 8:
        raise SourceError('Expediente incompleto')
    evidence = []
    for source in metadata:
        published = datetime.fromisoformat(source['published'])
        if published.tzinfo is None or not now - timedelta(hours=72) <= published <= now + timedelta(minutes=5):
            raise SourceError('Expediente desactualizado')
        if source.get('retrieval_method') == 'rss_full_content':
            feed = next((f for f in FEEDS if f.url == source.get('feed_url')), None)
            if not feed:
                raise SourceError('Feed no registrado')
            _, raw = await asyncio.to_thread(fetch, feed.url)
            row = next((r for r in parse_feed(raw, feed, now, max_age_hours=72) if r['url'] == source['url']), None)
            if not row or len(row.get('rss_text', '')) < 500:
                raise SourceError('Contenido RSS no disponible')
            evidence.append(dict(source, text=row['rss_text']))
            continue
        final, raw = await asyncio.to_thread(fetch, source['url'])
        if final != source['url']:
            raise SourceError('La fuente cambió de URL')
        if 'organization_verified' in source:
            attribution = source_attribution(final, raw, source['organization'])
            if any(attribution[key] != source[key] for key in ['organization', 'organization_verified']):
                raise SourceError('La autoría de la fuente cambió', 'source_identity_changed')
        evidence.append(dict(source, text=plain(raw), content_origin=content_origin(final, raw)))
    return evidence, {'candidate_count': len(evidence), 'fetch_failures': 0, 'resumed_review': True}
