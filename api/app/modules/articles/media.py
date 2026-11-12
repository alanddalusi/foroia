"""Owned graphics, bounded assets and evidence-bound multimedia. No model calls."""
import asyncio
import hashlib
import io
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,update
from PIL import Image,ImageDraw,ImageFont

from app.models import Article,ArticleAsset

VERSION='editorial-v3'

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Cover(Strict):
    src: str=Field(pattern=r'^/api/article-assets/[a-f0-9]{32}-1200\.png$')
    variants: dict[str,str]
    width: int=1200
    height: int=630
    alt: str=Field(min_length=10,max_length=300)
    caption: str=Field(max_length=300)
    credit: str='Foro IA al Día · composición original'
    rights: str='original'

class Video(Strict):
    id: str=Field(pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str=Field(min_length=3,max_length=200)
    source_url: str=Field(max_length=2000)
    provenance: str='embedded_by_official_source'

class ChartPoint(Strict):
    label: str=Field(min_length=2,max_length=80)
    value: float=Field(ge=0,le=1e15,allow_inf_nan=False)
    fragment_id: str=Field(pattern=r'^e_[a-f0-9]{32}$')

class Chart(Strict):
    title: str=Field(min_length=5,max_length=150)
    unit: str=Field(min_length=1,max_length=70)
    points: list[ChartPoint]=Field(min_length=2,max_length=6)
    source_url: str=Field(max_length=2000)

class Media(Strict):
    version: str=VERSION
    cover: Cover|None=None
    charts: list[Chart]=Field(default_factory=list,max_length=2)
    videos: list[Video]=Field(default_factory=list,max_length=2)


def official_videos(raw,url):
    """Only videos embedded in a retrieved original publisher page, not press.

    This attests the original page's embed, not an unverified uploader identity.
    No preview image or third-party request is made before the reader's choice.
    """
    from app.research.selection import PUBLISHERS
    from app.research.sources import NEWS_HOSTS
    org=PUBLISHERS.get(urlsplit(url).hostname) or NEWS_HOSTS.get(urlsplit(url).hostname)
    if org not in {'openai','anthropic','google','nvidia','microsoft','meta','tesla','xai','deepseek','oracle'}:return []
    class Embeds(HTMLParser):
        def __init__(self):super().__init__();self.items=[]
        def handle_starttag(self,tag,attrs):
            if tag!='iframe' or len(self.items)>=2:return
            a=dict(attrs)
            try:
                p=urlsplit(a.get('src',''))
                if p.scheme!='https' or p.hostname not in {'www.youtube.com','www.youtube-nocookie.com'} or p.username or p.password or p.port not in (None,443):return
            except ValueError:return
            match=re.fullmatch(r'/embed/([a-zA-Z0-9_-]{11})',p.path)
            title=(a.get('title') or '').strip()[:200]
            if len(title)<3:title='Vídeo enlazado por la fuente oficial'
            if match:self.items.append(Video(id=match[1],title=title,source_url=url).model_dump())
    parser=Embeds();parser.feed(raw.decode('utf-8',errors='replace'));return parser.items


def font(size,bold=False):
    names=[('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/dejavu/DejaVuSans.ttf'),
        ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
        ('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf')]
    for name in names:
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default(size=size)


def wrap(draw,text,fnt,width,max_lines):
    lines=[];current=''
    for word in text.split():
        trial=(current+' '+word).strip()
        if draw.textlength(trial,font=fnt)>width and current:lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    if len(lines)>max_lines:
        lines=lines[:max_lines];lines[-1]=lines[-1].rstrip('.,;:')+'…'
    return lines


def render(title,section,slug):
    """A labelled conceptual illustration, never a documentary image or fake data."""
    title=title.translate({ord(c):'-' for c in '‐‑‒–—'}).replace('\u00a0',' ')
    im=Image.new('RGB',(1200,630),'#f5f2e9');d=ImageDraw.Draw(im)
    seed=int(hashlib.sha256(slug.encode()).hexdigest()[:8],16)
    accent=['#9e4837','#255d56','#334d69','#68523c'][seed%4];ink='#202824'
    d.rectangle((0,0,1200,10),fill=accent)
    d.text((64,48),'FORO IA AL DÍA',font=font(20,True),fill=ink)
    d.text((64,104),section.upper(),font=font(17),fill=accent)
    for n,line in enumerate(wrap(d,title,font(43,True),660,5)):
        d.text((60,165+n*57),line,font=font(43,True),fill=ink)
    d.line((64,530,700,530),fill='#bdbbad',width=2)
    d.text((64,556),'ILUSTRACIÓN EDITORIAL · NO ES UNA FOTOGRAFÍA',font=font(15),fill='#555d56')
    lower=title.lower()
    if section in {'programacion','tutoriales'}:
        labels=['DATOS','VALIDACIÓN','RESULTADO']
        if 'pdf' in lower:labels=['DOCUMENTO','EXTRACCIÓN','REVISIÓN']
        elif 'json' in lower:labels=['JSON','ESQUEMA','VALIDACIÓN']
        for i,label in enumerate(labels):
            y=145+i*115
            d.rounded_rectangle((790,y,1132,y+78),radius=10,fill='white',outline=accent,width=3)
            d.text((813,y+25),label,font=font(23,True),fill=ink)
            if i<2:d.line((958,y+78,958,y+115),fill=accent,width=4)
    elif re.search(r's[‑-]?1|bolsa|document',lower):
        d.rounded_rectangle((810,130,1110,490),radius=12,fill='white',outline=accent,width=3)
        tag='S-1' if 's' in lower and 'bolsa' in lower else 'DOCUMENTO'
        d.text((845,170),tag,font=font(46,True),fill=accent)
        for n in range(5):d.line((845,265+n*31,1070-(n%2)*40,265+n*31),fill='#c9cec6',width=6)
        d.ellipse((1010,440,1120,550),fill=accent)
        d.text((1036,467),'IA',font=font(36,True),fill='white')
    else:
        terms=[w.strip('.,:«»') for w in title.split() if len(w)>4][:3]
        for n,term in enumerate(terms or ['Inteligencia','Artificial']):
            y=170+n*105;x=800+(n%2)*20
            d.rounded_rectangle((x,y,1130,y+78),radius=8,fill=accent if n==0 else 'white',outline=accent,width=2)
            label=wrap(d,term.upper(),font(23,True),285,1)[0]
            d.text((x+20,y+23),label,font=font(23,True),fill='white' if n==0 else ink)
    out={}
    for width in [480,800,1200]:
        resized=im if width==1200 else im.resize((width,round(width*630/1200)),Image.Resampling.LANCZOS)
        buf=io.BytesIO();resized.save(buf,'WEBP',quality=83,method=5);out[f'{width}.webp']=buf.getvalue()
    buf=io.BytesIO();im.save(buf,'PNG',optimize=True);out['1200.png']=buf.getvalue()
    return out


def revenue_chart(article,evidence):
    """Only an unambiguous same-unit/same-period comparison from one excerpt.

    No chart from arbitrary numbers, inferred dates or growth estimates.
    """
    from app.research.writing import supported_number
    for source in evidence:
        if source['url'] not in {s['url'] for s in article.sources}:continue
        for f in source.get('fragments',[]):
            text=f['text']
            pattern=r'revenue of \$(\d+(?:\.\d+)?) billion for the first half of (20\d\d),?\s+(?:up from|down from|compared with|compared to)\s+\$(\d+(?:\.\d+)?) billion\s+(?:in|for) the same period(?: of)?\s+(20\d\d|last year)'
            match=re.search(pattern,text,re.I)
            if not match:continue
            a,ya,b,yb=match.groups()
            if yb.lower()=='last year':yb=str(int(ya)-1)
            if not all(supported_number(v,article.body) for v in [a,ya,b,yb]):continue
            return [Chart(title='Ingresos del primer semestre',unit='Miles de millones de USD',source_url=source['url'],
                points=[ChartPoint(label=yb,value=float(b),fragment_id=f['fragment_id']),ChartPoint(label=ya,value=float(a),fragment_id=f['fragment_id'])]).model_dump()]
    return []


async def ensure_media(db,article,evidence=()):
    """Publish assets and metadata atomically with the article in the existing DB.

    Only owned compositions are currently approved; no remote photograph is
    downloaded based on og:image, a filename, or a model's licence assertion.
    """
    fingerprint=hashlib.sha256((VERSION+'|'+article.slug+'|'+article.title+'|'+article.section+'|'+article.body).encode()).hexdigest()[:32]
    if article.media and (article.media.get('cover') or {}).get('src')==f'/api/article-assets/{fingerprint}-1200.png':return
    assets=await asyncio.to_thread(render,article.title,article.section,article.slug)
    variants={}
    for spec,data in assets.items():
        key=f'{fingerprint}-{spec}'
        if not await db.get(ArticleAsset,key):db.add(ArticleAsset(key=key,article_id=article.id,content_type='image/webp' if spec.endswith('webp') else 'image/png',content=data,sha256=hashlib.sha256(data).hexdigest()))
        if spec.endswith('webp'):variants[spec.split('.')[0]]=f'/api/article-assets/{key}'
    videos=[]
    for source in evidence:
        if not source.get('organization_verified') or source['url'] not in {s['url'] for s in article.sources}:continue
        for raw in source.get('official_videos',[])[:1]:
            video=Video.model_validate(raw)
            if video.source_url==source['url']:videos.append(video)
    media=Media(cover=Cover(src=f'/api/article-assets/{fingerprint}-1200.png',variants=variants,
        alt=('Ilustración conceptual: '+article.title)[:300],caption='Composición original sobre el tema del artículo; no representa una fotografía del acontecimiento.'),
        charts=revenue_chart(article,evidence),videos=videos[:1]).model_dump()
    # Presentation enrichment does not forge a content-update timestamp.
    await db.execute(update(Article).where(Article.id==article.id).values(media=media,updated_at=article.updated_at))
    article.media=media
    await db.flush()
