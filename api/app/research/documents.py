"""Bounded official-document cache, including negative cache; no open-web fetches."""
import asyncio
import hashlib
import http.client
from datetime import UTC, timedelta
from urllib.parse import urlsplit

from app.models import SourceCache
from app.research.sources import DOCUMENT_HOSTS, SourceError, canonical, fetch, plain

# Public Markdown representations verified against Google AI Studio on 8/11.
# No login, private endpoint, generic URL guessing or blocked-page proxying.
GOOGLE_DOCUMENTS = frozenset({'get-started','pricing','tokens','embeddings','prompting-strategies'})


def documentation_url(url):
    url=canonical(url)
    p=urlsplit(url)
    prefix='/gemini-api/docs/' if p.hostname=='ai.google.dev' else '/docs/' if p.hostname=='aistudio.google.com' else None
    if prefix and p.path.startswith(prefix) and p.path[len(prefix):] in GOOGLE_DOCUMENTS:
        return canonical('https://aistudio.google.com/docs/'+p.path[len(prefix):]+'.md')
    return url


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def document_text(raw):
    # Isolate main/article when available, then reuse the hardened text-only extractor.
    import re
    html=raw.decode('utf-8',errors='replace')
    match=re.search(r'<(?:main|article)\b[^>]*>(.*?)</(?:main|article)>',html,re.I|re.S)
    # Keep bounded official manuals long enough to select the verified API
    # passages (casefold/SQLite clauses occur deep in Python's manuals). The
    # writer's catalogue remains limited to 18k and its context to 24k bytes.
    return plain(match.group(1).encode() if match else raw,max_chars=300_000)


def document_sections(raw):
    import re
    html=raw.decode('utf-8',errors='replace')
    chunks=[]
    for match in re.finditer(r'<h[23]\b([^>]*)>(.*?)</h[23]>(.*?)(?=<h[23]\b|$)',html,re.I|re.S):
        title=plain(match.group(2).encode()).strip('¶ #')[:120]
        anchor=re.search(r'(?:id|href)=["\']#?([a-zA-Z0-9_.:-]{1,120})["\']',match.group(1)+' '+match.group(2))
        chunks.append((title,match.group(3),anchor.group(1) if anchor else None))
    if not chunks:
        chunks=[(m.group(1).strip(),m.group(2),None) for m in re.finditer(r'^#{2,3}\s+([^\n]+)\n(.*?)(?=^#{2,3}\s|\Z)',html,re.M|re.S)]
    result=[]
    for title,body,anchor in chunks:
        text=plain(body.encode())[:8000]
        if len(text)<900 or title.lower() in {'navigation','table of contents','related pages','on this page'}:continue
        result.append({'key':hashlib.sha256(title.lower().encode()).hexdigest()[:24],'title':title,'anchor':anchor,'text':text})
        if len(result)==8:break
    return result


async def official_document(db,url,now,budget,fetcher=fetch):
    url=documentation_url(url)
    if urlsplit(url).hostname not in DOCUMENT_HOSTS:raise SourceError('Documento no registrado','unregistered_document')
    cached=await db.get(SourceCache,url)
    if cached and aware(cached.expires_at)>now:
        if cached.document.get('error'):raise SourceError('Fuente en espera',cached.document['error'],cached.document.get('http_status'))
        return dict(cached.document,cache_hit=True)
    if budget['remaining']<=0:raise SourceError('Límite de documentos','document_fetch_budget')
    budget['remaining']-=1
    try:
        final,raw=await asyncio.to_thread(fetcher,url)
        org=DOCUMENT_HOSTS.get(urlsplit(final).hostname)
        if not org:raise SourceError('Organización no registrada','unregistered_document')
        text=document_text(raw)
        if len(text)<500:raise SourceError('Documentación insuficiente','short_document')
        sha=hashlib.sha256(text.encode()).hexdigest()
        title=text.split('¶')[0][:160].strip() or urlsplit(final).path
        document={'id':int(hashlib.sha256(final.encode()).hexdigest()[:12],16),'url':final,'title':title,
            'language':'en','organization':org,'organization_verified':True,'platform':urlsplit(final).hostname,
            'published':None,'retrieved_at':now.isoformat(),'date_kind':'retrieved','text':text,
            'kind':'official_documentation','retrieval_method':'official_document','content_sha256':sha,'sections':document_sections(raw)}
        expiry=now+timedelta(hours=24)
    except (OSError,ValueError,SourceError,http.client.HTTPException) as exc:
        code=exc.code if isinstance(exc,SourceError) else 'document_unavailable'
        document={'url':url,'error':code,'http_status':getattr(exc,'http_status',None)};sha=hashlib.sha256(b'').hexdigest();expiry=now+timedelta(hours=2)
        if cached:cached.document,cached.content_sha256,cached.fetched_at,cached.expires_at=document,sha,now,expiry
        else:db.add(SourceCache(url=url,document=document,content_sha256=sha,fetched_at=now,expires_at=expiry))
        await db.commit()
        raise SourceError('Documento no disponible',code,getattr(exc,'http_status',None)) from None
    if cached:cached.document,cached.content_sha256,cached.fetched_at,cached.expires_at=document,sha,now,expiry
    else:db.add(SourceCache(url=url,document=document,content_sha256=sha,fetched_at=now,expires_at=expiry))
    await db.commit()
    return document
