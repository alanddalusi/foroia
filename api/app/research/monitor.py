"""Existing host health timer's editorial/SEO checks. No model or generation imports."""
import asyncio,json
from datetime import timedelta,datetime,UTC
from urllib.parse import urlsplit
from xml.etree import ElementTree
from sqlalchemy import select,func,text
from app.models import Article,ResearchRun,ResearchControl,EditorialCandidate,AuditLog,NewsScan,utcnow
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.limits import get_redis
from app.research.config import settings,MADRID
from app.research.publication import Page,get_own
from app.research.seo import description
from app.research.documents import aware

KEY='foroia:editorial:health'


def locations(raw,site):
    if '<!DOCTYPE' in raw.upper():raise ValueError('unsafe_xml')
    rows=[n.text for n in ElementTree.fromstring(raw).iter() if n.tag.endswith('}loc')]
    for url in rows:
        p=urlsplit(url or '')
        if p.scheme!='https' or p.netloc!=urlsplit(site).netloc or p.query or p.fragment or p.username:raise ValueError('noncanonical_sitemap_url')
    if len(rows)!=len(set(rows)):raise ValueError('duplicate_sitemap_url')
    return rows


async def inspect(db,redis,now=None,getter=None):
    now=now or utcnow();site=get_settings().site_url;config=settings();alerts=[]
    get=getter or (lambda url:get_own(url,site,timeout=3))
    async def request(path):return await asyncio.to_thread(get,site+path)
    await db.scalar(text('SELECT 1'))
    control=await db.get(ResearchControl,1)
    alive=bool(await redis.get('foroia:research:heartbeat'))
    if control and control.enabled and not alive:alerts.append('worker_heartbeat_missing')
    rapid_state=None
    local=now.astimezone(MADRID);month=local.date().replace(day=1)
    reserved=await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd),0)).where(ResearchRun.editorial_date>=month))
    if reserved>=int(config.monthly_usd*1_000_000):alerts.append('monthly_budget_exhausted')
    today=await db.scalar(select(ResearchRun).where(ResearchRun.editorial_date==local.date()))
    scheduled=datetime.combine(local.date(),config.at,tzinfo=MADRID)
    if control and control.enabled and local>scheduled+timedelta(minutes=20):
        if not today:alerts.append('scheduled_run_missing')
        elif today.status=='running' and aware(today.created_at)<now-timedelta(minutes=20):alerts.append('run_stalled')
        elif today.reason in {'internal_error','candidate_internal_error','timeout','worker_interrupted'}:alerts.append('editorial_run_failed')
        elif today.status=='skipped' and today.reason not in {'weekly_target_reached','migrated_local_budget'}:
            start=datetime.combine(local.date(),datetime.min.time(),tzinfo=MADRID).astimezone(UTC)
            # A verified manual publication shares the budget, not the daily run's status.
            published=await db.scalar(select(EditorialCandidate.id).join(Article,Article.id==EditorialCandidate.article_id).where(
                EditorialCandidate.state=='published',EditorialCandidate.published_at>=start,Article.status=='published').limit(1))
            if not published:alerts.append('no_publication_today')
    if await db.scalar(select(EditorialCandidate.id).where(EditorialCandidate.state=='needs_verification',EditorialCandidate.updated_at<now-timedelta(minutes=10)).limit(1)):
        alerts.append('publication_verification_stalled')
    article_count=await db.scalar(select(func.count()).select_from(Article).where(Article.status=='published'))
    last=await db.scalar(select(func.max(Article.published_at)).where(Article.status=='published'))
    latest=await db.scalar(select(ResearchRun).order_by(ResearchRun.editorial_date.desc()).limit(1))
    source_stats=(latest.report.get('news_discovery',{}).get('statistics') or latest.report) if latest else {}
    discovery=latest.report.get('news_discovery',{}) if latest else {}
    web=discovery.get('web') or (latest.report.get('web_research',{}) if latest else {})
    if web.get('research_status')=='invalid' or web.get('state') in {'calling','failed'}:
        alerts.append('news_research_failed')
    elif web.get('research_status')=='empty' or (web.get('state')=='response' and source_stats.get('candidate_count')==0):
        alerts.append('news_research_empty')
    elif web.get('verification_status')=='no_verified_candidates':alerts.append('news_verification_exhausted')
    source_errors=source_stats.get('fetch_errors',[])
    codes={row.get('http_status') for row in source_errors}
    if 403 in codes:alerts.append('source_http_403')
    seo={'sitemap_urls':None,'sitemap_files':None,'sampled_articles':0,'published_articles':article_count,
         'all_articles_checked':article_count==0,'indexation':'not_measured','orphan_detection':'not_measured'}
    try:
        home=Page(await request('/'))
        if home.canonical!=[site+'/'] or 'noindex' in home.meta.get('robots','').lower():raise ValueError('homepage_not_canonical_or_indexable')
        robots=await request('/robots.txt')
        if 'Sitemap: '+site+'/sitemap.xml' not in robots or any(line.strip().lower()=='disallow: /' for line in robots.splitlines()):raise ValueError('robots_invalid')
        children=locations(await request('/sitemap.xml'),site)
        if len(children)>4:
            seo['sitemap_scope']='first_four_files'
        urls=[]
        for child in children[:4]:urls.extend(locations(await asyncio.to_thread(get,child),site))
        if len(urls)!=len(set(urls)):raise ValueError('duplicate_sitemap_url')
        seo.update(sitemap_urls=len(urls),sitemap_files=min(4,len(children)),sitemap_scope='complete' if len(children)<=4 else 'first_four_files')
        offset=(int(now.timestamp())//300*3)%max(1,article_count)
        sample=(await db.scalars(select(Article).where(Article.status=='published').order_by(Article.id).offset(offset).limit(3))).all()
        for article in sample:
            url=site+'/articulos/'+article.slug
            if url not in urls:
                if len(children)>4:continue  # Not a claim about an unscanned sitemap.
                raise ValueError('published_article_missing_sitemap')
            page=Page(await asyncio.to_thread(get,url))
            if page.canonical!=[url] or page.meta.get('description')!=description(article.summary) or 'noindex' in page.meta.get('robots','').lower():
                seo['failed_url']=url
                seo['mismatch']={'canonical':page.canonical!=[url],
                    'description':page.meta.get('description')!=description(article.summary),
                    'noindex':'noindex' in page.meta.get('robots','').lower()}
                raise ValueError('article_seo_mismatch')
            seo['sampled_articles']+=1
        seo['all_articles_checked']=seo['sampled_articles']==article_count
        linked=set(home.links)
        if article_count<=50:
            slugs=(await db.scalars(select(Article.slug).where(Article.status=='published'))).all()
            if all('/articulos/'+slug in linked or site+'/articulos/'+slug in linked for slug in slugs):
                seo.update(orphan_detection='all_published_articles_linked_from_home',orphan_articles=[])
    except Exception as exc:
        allowed={'unsafe_xml','noncanonical_sitemap_url','duplicate_sitemap_url','homepage_not_canonical_or_indexable','robots_invalid','published_article_missing_sitemap','article_seo_mismatch'}
        alerts.append(str(exc) if str(exc) in allowed else 'public_seo_check_failed')
    report={'checked_at':now.isoformat(),'worker_alive':alive,'rapid':rapid_state,'alerts':sorted(set(alerts)),
        'seo':seo,'last_publication_at':aware(last).isoformat() if last else None,
        'last_run':{'date':str(latest.editorial_date),'status':latest.status,'reason':latest.reason} if latest else None,
        'notification_channel':'systemd_journal_and_private_panel','external_notifications_configured':False}
    previous=await redis.get(KEY)
    try:old=json.loads(previous) if previous else {}
    except (ValueError,TypeError):old={}
    if old.get('alerts',[])!=report['alerts']:
        db.add(AuditLog(actor='monitor',action='editorial_health_changed',entity_type='research',entity_id=1,
            details={'alerts':report['alerts'],'previous_alerts':old.get('alerts',[])}))
        await db.commit()
    await redis.set(KEY,json.dumps(report),ex=1800)
    return report


async def main():
    try:
        async with get_sessionmaker()() as db:report=await inspect(db,get_redis())
        print(json.dumps({'event':'editorial_health','alerts':report['alerts'],'seo':report['seo']}),flush=True)
        return 1 if set(report['alerts'])-{'source_http_403','no_publication_today','news_research_empty','news_verification_exhausted'} else 0
    except Exception:
        print(json.dumps({'event':'editorial_health_unavailable','reason':'database_redis_or_monitor_error'}),flush=True)
        return 1


if __name__=='__main__':raise SystemExit(asyncio.run(main()))
