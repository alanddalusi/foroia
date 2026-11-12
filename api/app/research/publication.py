"""Post-publication verification and guarded withdrawal; no model calls."""
import asyncio
from datetime import UTC,datetime,timedelta
from html.parser import HTMLParser
import http.client
import json
import re
import ssl
from urllib.parse import urlsplit
from xml.etree import ElementTree

from sqlalchemy import select,func
from app.core.config import get_settings
from app.models import Article,EditorialCandidate,ResearchRun,AuditLog,utcnow
from app.research.documents import aware
from app.research.seo import description

FIELDS=('id','slug','title','summary','body','section','author_name','sources','status','comments_enabled','published_at','updated_at','reviewed_at','reviewed_by')


def article_snapshot(article):
    return {k:aware(v).isoformat() if isinstance(v:=getattr(article,k),datetime) else v for k in FIELDS}


class PublicationError(Exception):
    def __init__(self,code,transient=False):super().__init__(code);self.transient=transient


class Page(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.meta={};self.canonical=[];self.links=[];self.h1='';self.title='';self.text='';self.stack=[];self.ld=[];self.script=None
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag not in {'img','meta','link','br','hr','input','source','wbr'}:self.stack.append(tag)
        if tag=='meta':self.meta[a.get('name') or a.get('property')]=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag=='script' and a.get('type')=='application/ld+json':self.script=''
    def handle_data(self,data):
        if self.script is not None:self.script+=data
        if not any(t in self.stack for t in ['script','style','noscript']):
            self.text+=' '+data
            if 'h1' in self.stack:self.h1+=data
            if 'title' in self.stack:self.title+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            try:
                value=json.loads(self.script)
                if isinstance(value,list):self.ld.extend(v for v in value if isinstance(v,dict))
                elif isinstance(value,dict):self.ld.extend(value.get('@graph',[value]))
            except ValueError:raise PublicationError('invalid_jsonld') from None
            self.script=None
        if tag in self.stack:self.stack=self.stack[:len(self.stack)-1-self.stack[::-1].index(tag)]


def get_own(url,site,timeout=12):
    p=urlsplit(url);base=urlsplit(site)
    if p.scheme!='https' or p.netloc!=base.netloc or p.username or p.password:
        raise PublicationError('unsafe_publication_url')
    connection=http.client.HTTPSConnection(p.hostname,timeout=timeout,context=ssl.create_default_context())
    try:
        connection.request('GET',p.path or '/',headers={'User-Agent':'ForoIA publication verification'})
        response=connection.getresponse();raw=response.read(2_000_001)
        if response.status!=200:raise PublicationError('publication_http_'+str(response.status),response.status>=500 or response.status==429)
        if len(raw)>2_000_000:raise PublicationError('publication_response_too_large')
        return raw if response.getheader('Content-Type','').startswith('image/') else raw.decode('utf-8')
    except (OSError,http.client.HTTPException):raise PublicationError('publication_network_error',True) from None
    finally:connection.close()


def verify_html(snapshot,site,sitemap_page,getter=None):
    get=getter or (lambda url:get_own(url,site))
    url=site+'/articulos/'+snapshot['slug'];page=Page(get(url))
    compact=lambda s:re.sub(r'\s+',' ',s).strip()
    if page.canonical!=[url] or compact(page.h1)!=compact(snapshot['title']) or not compact(page.title).startswith(compact(snapshot['title'])):raise PublicationError('publication_canonical_or_heading')
    if page.meta.get('description')!=description(snapshot['summary']) or 'noindex' in page.meta.get('robots','').lower():raise PublicationError('publication_not_indexable')
    if page.meta.get('og:title')!=snapshot['title'] or page.meta.get('og:description')!=description(snapshot['summary']):raise PublicationError('publication_social_metadata')
    body=json.loads(get(site+'/api/articles/'+snapshot['slug']))
    if any(body.get(k)!=snapshot[k] for k in ['slug','title','summary','body','section','sources']):raise PublicationError('publication_api_mismatch')
    for heading in re.findall(r'^##\s+(.+)$',snapshot['body'],re.M):
        if compact(heading) not in compact(page.text):raise PublicationError('publication_missing_ssr_content')
    first=next((line for line in snapshot['body'].splitlines() if line.strip() and not line.startswith(('##','```'))),'')
    first=re.sub(r'[`*]','',first)[:80]
    if first and compact(first) not in compact(page.text):raise PublicationError('publication_missing_ssr_content')
    allowed={'Article','BlogPosting','NewsArticle'} if snapshot['section']=='actualidad' else {'Article','BlogPosting'}
    articles=[s for s in page.ld if allowed.intersection([s.get('@type')] if isinstance(s.get('@type'),str) else s.get('@type',[]))]
    if not articles or articles[0].get('headline')!=snapshot['title'] or not any(s.get('@type')=='BreadcrumbList' for s in page.ld):raise PublicationError('publication_schema_mismatch')
    schema=articles[0]
    if schema.get('mainEntityOfPage')!=url or schema.get('citation')!=[s['url'] for s in snapshot['sources']]:raise PublicationError('publication_schema_mismatch')
    try:
        for field,key in [('datePublished','published_at'),('dateModified','updated_at')]:
            if aware(datetime.fromisoformat(schema[field].replace('Z','+00:00')))!=aware(datetime.fromisoformat(snapshot[key])):raise PublicationError('publication_schema_dates')
    except (ValueError,KeyError,TypeError):raise PublicationError('publication_schema_dates') from None
    image=page.meta.get('og:image','')
    if not image.startswith(site+'/'):raise PublicationError('publication_image_missing')
    cover=(body.get('media') or {}).get('cover')
    if cover and (image!=site+cover['src'] or schema.get('image')!=[image]):raise PublicationError('publication_image_mismatch')
    get(image)
    locations=lambda xml:{n.text for n in ElementTree.fromstring(xml).iter() if n.tag.endswith('}loc')}
    child=site+'/sitemaps/articles/'+str(sitemap_page)
    if child not in locations(get(site+'/sitemap.xml')) or url not in locations(get(child)):raise PublicationError('publication_missing_sitemap',True)
    return {'url':url,'html':True,'api':True,'seo':True,'sitemap':True,'image':True}


async def verify_candidate(db,candidate,verifier=None,now=None):
    from app.models import EditorialCandidate
    candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.id==candidate.id)
        .with_for_update().execution_options(populate_existing=True))
    if candidate.state=='published':
        await db.commit()
        return True
    now=now or utcnow()
    article=await db.get(Article,candidate.article_id,populate_existing=True)
    snapshot=candidate.details.get('publication_snapshot')
    if not article or not snapshot or article_snapshot(article)!=snapshot:
        candidate.state='rejected';candidate.reason='article_changed';await db.commit();return False
    rank=await db.scalar(select(func.count()).select_from(Article).where(Article.status=='published',Article.id<=article.id))
    page=max(1,(rank+4999)//5000)
    attempts=int(candidate.details.get('verification_attempts',0))+1
    try:
        result=await verifier(snapshot,page) if verifier else await asyncio.to_thread(verify_html,snapshot,get_settings().site_url,page)
        if not result or not all(result.get(k) for k in ['html','api','seo','sitemap','image']):raise PublicationError('publication_verification_incomplete')
    except Exception as exc:
        code=str(exc) if isinstance(exc,PublicationError) else 'publication_verification_error'
        candidate.details=dict(candidate.details,verification_attempts=attempts,verification_error=code)
        if (not isinstance(exc,PublicationError) or exc.transient) and attempts<3:
            candidate.next_attempt_at=now+timedelta(seconds=30);await db.commit();return False
        # Recheck under lock: never overwrite a subsequent human edit.
        article=await db.scalar(select(Article).where(Article.id==candidate.article_id).with_for_update().execution_options(populate_existing=True))
        if article_snapshot(article)==snapshot:
            old=candidate.details.get('previous_revision')
            if old:
                for key,value in old.items():
                    if key=='id':continue
                    if key.endswith('_at') and value:value=datetime.fromisoformat(value)
                    setattr(article,key,value)
            else:article.status='archived'
        retry=isinstance(exc,PublicationError) and exc.transient and candidate.attempts<2
        recoverable=int(candidate.details.get('publication_recoveries',0))<2 and bool(candidate.details.get('editorial_record'))
        candidate.state='publication_error' if recoverable else 'technical_error';candidate.reason='publication_check_failed'
        candidate.next_attempt_at=now+timedelta(hours=6) if recoverable else None
        await db.flush()
        candidate.details=dict(candidate.details,withdrawal_snapshot=article_snapshot(article))
        db.add(AuditLog(actor='automation',action='publication_withdrawn',entity_type='article',entity_id=article.id,details={'candidate_id':candidate.id,'reason':code}))
        await db.commit();return False
    candidate.state='published';candidate.reason='verified_publication';candidate.published_at=now;candidate.next_attempt_at=None
    candidate.details=dict(candidate.details,verification_attempts=attempts,verification=result)
    db.add(AuditLog(actor='automation',action='publication_verified',entity_type='article',entity_id=article.id,details={'candidate_id':candidate.id}))
    await db.commit();return True
