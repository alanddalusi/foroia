"""Free 30-minute observation; dispatches the existing durable editorial jobs."""
import asyncio,hashlib,http.client,json,secrets
from email.utils import parsedate_to_datetime
from datetime import UTC,datetime,timedelta
from xml.etree import ElementTree
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.models import NewsScan,NewsFeedState,NewsObservation,ResearchControl,EditorialCandidate,EditorialExecution,Article,AuditLog,utcnow
from app.core.db import get_sessionmaker
from app.core.limits import get_redis
from app.research import sources
from app.research.documents import aware
from app.research.events import identify
from app.research.queue import upsert_event,fingerprint
from app.research.config import settings,MADRID
from app.research.writing import StopRun

SCAN_LOCK='foroia:research:news-scan'
INTERVAL=timedelta(minutes=30)
FEEDS=tuple(f for f in (*sources.FEEDS,*sources.RAPID_FEEDS) if f.organization!='unverified_scientific_authors')

def window(now):
    now=now.astimezone(UTC)
    return now.replace(minute=now.minute//30*30,second=0,microsecond=0)

def retry_time(now,attempt,exc):
    if getattr(exc,'http_status',None)==403:return now+timedelta(hours=6)
    delay=timedelta(minutes=min(240,30*2**min(attempt-1,3)))
    if getattr(exc,'http_status',None)==429:
        try:delay=max(delay,timedelta(seconds=min(86400,max(1800,int(exc.retry_after)))))
        except (ValueError,TypeError,AttributeError):
            try:delay=max(delay,min(timedelta(days=1),aware(parsedate_to_datetime(exc.retry_after))-now))
            except (ValueError,TypeError,AttributeError,OverflowError):pass
    return now+delay

async def read(fetcher,url,limit):
    return await asyncio.wait_for(asyncio.to_thread(fetcher,url,limit),timeout=55)

async def observe(db,scan,now,fetcher=sources.fetch,feeds=FEEDS):
    """No model imports/calls. RSS nominates documents, never supplies invented facts."""
    report={'version':1,'model_calls':0,'feed_count':len(feeds[:12]),'feeds_attempted':0,'feeds_checked':0,'feed_backoff':0,'entries':0,'documents':0,
        'already_seen':0,'nominated':[],'accepted':[],'rejected':[],'errors':[],'article_fetches':0}
    for feed in feeds[:12]:
        state=await db.get(NewsFeedState,feed.url)
        if not state:state=NewsFeedState(url=feed.url);db.add(state);await db.flush()
        if state.retry_at and aware(state.retry_at)>now:report['feed_backoff']+=1;continue
        report['feeds_attempted']+=1
        try:
            _,raw=await read(fetcher,feed.url,sources.MAX_BYTES)
            rows=sources.parse_news_index(raw,feed) if feed.kind=='html' else sources.parse_feed(raw,feed,now,max_age_hours=24*365*50)
            report['feeds_checked']+=1
            state.checked_at=now;state.failures=0;state.reason='';state.retry_at=None
            for row in rows[:30]:
                report['entries']+=1
                key=fingerprint(row['url']);old=await db.get(NewsObservation,key)
                if old:report['already_seen']+=1;continue
                # HTML indexes may omit dates/product names. Fetch to establish them.
                event=identify(row)
                reason='' if event or not row.get('published') else 'no_named_announcement'
                stamp=datetime.fromisoformat(row['published']) if row.get('published') else None
                if stamp and now-aware(stamp)>timedelta(hours=48):reason='stale_announcement'
                db.add(NewsObservation(key=key,url=row['url'],feed_url=feed.url,published_at=stamp,
                    first_seen_at=now,state='ignored' if reason else 'pending',reason=reason,data=row))
                if reason:report['rejected'].append({'url':row['url'],'reason':reason})
        except (OSError,ValueError,sources.SourceError,ElementTree.ParseError,TimeoutError,http.client.HTTPException) as exc:
            state.failures+=1;state.checked_at=now;state.reason=getattr(exc,'code','feed_unavailable');state.retry_at=retry_time(now,state.failures,exc)
            report['errors'].append(sources.failure_details(feed.url,'feed',exc))
        await db.commit()
    nominations=(await db.scalars(select(NewsObservation).where(NewsObservation.candidate_id.is_(None),NewsObservation.state.in_(['pending','blocked']),
        NewsObservation.published_at>=now-timedelta(hours=48)).order_by(NewsObservation.first_seen_at.desc()).limit(200))).all()
    for observation in nominations:
        if not (event:=identify(observation.data)):continue
        # Metadata nominates an opportunity, never a verified quotation or a drafting permit.
        provisional={k:v for k,v in observation.data.items() if k not in {'rss_text','feed_url'}}
        provisional.update(id=int(observation.key[:12],16),text='',organization_verified=False)
        candidate=await upsert_event(db,[provisional],event,now)
        observation.candidate_id=candidate.id
        report['nominated'].append({'candidate_id':candidate.id,'url':observation.url,'reason':'waiting_verified_sources'})
        await db.commit()
    pending=(await db.scalars(select(NewsObservation).where(NewsObservation.state=='pending',
        (NewsObservation.retry_at.is_(None))|(NewsObservation.retry_at<=now)).order_by(NewsObservation.first_seen_at.desc(),NewsObservation.key).limit(200))).all()
    # Explicit named/current announcements precede undated generic HTML index links.
    pending=sorted(pending,key=lambda r:(identify(r.data) is None,-(aware(r.published_at).timestamp() if r.published_at else 0),r.key))[:12]
    for observation in pending:
        if observation.attempts>=3:
            observation.state='blocked';observation.reason='source_retry_limit';await db.commit();continue
        row=observation.data
        if observation.published_at and now-aware(observation.published_at)>timedelta(hours=48):
            observation.state='ignored';observation.reason='stale_announcement';await db.commit();continue
        observation.attempts+=1;report['article_fetches']+=1
        try:
            try:
                final,raw=await read(fetcher,observation.url,sources.MAX_BYTES)
                stamp=sources.article_date(raw)
                # Original publication date takes precedence over a changed RSS timestamp.
                if stamp and not now-timedelta(hours=48)<=stamp<=now+timedelta(minutes=5):
                    raise StopRun('old_article_updated')
                stamp=stamp or (aware(observation.published_at) if observation.published_at else None)
                if not stamp:raise StopRun('unverified_publication_date')
                text=sources.plain(raw);attribution=sources.source_attribution(final,raw,row['organization'])
                origin=sources.content_origin(final,raw);method='page'
            except sources.SourceError as exc:
                if exc.http_status!=403 or len(row.get('rss_text',''))<500:raise
                # Explicit publisher full-content RSS is an allowed representation, never a bypass.
                final=observation.url;stamp=aware(observation.published_at) if observation.published_at else None
                if not stamp:raise StopRun('unverified_publication_date')
                text=row['rss_text'];attribution=sources.source_attribution(final,b'',row['organization']);origin=final;method='rss_full_content'
                report['errors'].append(sources.failure_details(final,'article',exc))
            if len(text)<500:raise StopRun('short_document')
            document={k:v for k,v in row.items() if k not in {'rss_text','feed_url'}}
            document.update(id=int(hashlib.sha256(final.encode()).hexdigest()[:12],16),url=final,text=text,published=stamp.isoformat(),
                retrieved_at=now.isoformat(),content_origin=origin,retrieval_method=method,**attribution)
            event=identify(document)
            if not event:raise StopRun('no_named_announcement')
            candidate=await upsert_event(db,[document],event,now)
            observation.candidate_id=candidate.id;observation.state='recorded';observation.reason=candidate.reason or 'corroborated_named_event'
            observation.data={k:v for k,v in row.items() if k!='rss_text'}
            report['documents']+=1;report['accepted'].append({'url':final,'candidate_id':candidate.id,'event':event,'state':candidate.state,'reason':observation.reason})
        except StopRun as exc:
            observation.state='ignored';observation.reason=str(exc);report['rejected'].append({'url':observation.url,'reason':str(exc)})
            if observation.candidate_id and str(exc)=='old_article_updated':
                candidate=await db.get(EditorialCandidate,observation.candidate_id)
                if candidate and not candidate.attempts and not any(s.get('organization_verified') and len(s.get('text',''))>=500 for s in candidate.details.get('sources',[])):
                    candidate.state='rejected';candidate.reason='old_article_updated'
        except (OSError,ValueError,sources.SourceError,TimeoutError,http.client.HTTPException) as exc:
            observation.reason=getattr(exc,'code','document_unavailable');observation.retry_at=retry_time(now,observation.attempts,exc)
            if observation.attempts>=3:observation.state='blocked'
            report['errors'].append(sources.failure_details(observation.url,'article',exc))
        await db.commit()
    # Audit summaries stay bounded; exact accepted source text lives in the existing queue.
    report['rejected']=report['rejected'][:60];report['accepted']=report['accepted'][:12];report['nominated']=report['nominated'][:30]
    scan.report=report;scan.state='completed';scan.finished_at=now;await db.commit()
    print(json.dumps({'event':'news_scan_completed','scan_id':scan.id,**{k:report[k] for k in ['feeds_checked','documents','already_seen','article_fetches','model_calls']}}),flush=True)
    return report

async def tick(now=None,fetcher=sources.fetch,feeds=FEEDS):
    now=now or utcnow();redis=get_redis();token=secrets.token_hex(24).encode()
    from app.research.worker import RELEASE
    if not await redis.set(SCAN_LOCK,token,nx=True,ex=600):return
    try:
        async with get_sessionmaker()() as db:
            control=await db.get(ResearchControl,1)
            if not control or not control.enabled or not control.rapid_enabled:return
            stale=(await db.scalars(select(NewsScan).where(NewsScan.state=='running',NewsScan.created_at<now-timedelta(minutes=10)))).all()
            for previous in stale:
                previous.state='interrupted';previous.finished_at=now;previous.report=dict(previous.report,error='scan_interrupted',model_calls=0)
            await db.commit()
            if await db.scalar(select(NewsScan.id).where(NewsScan.window==window(now))):return
            scan=NewsScan(window=window(now),created_at=now);db.add(scan)
            try:await db.commit()
            except IntegrityError:await db.rollback();return
            sid=scan.id
            try:await asyncio.wait_for(observe(db,scan,now,fetcher,feeds),timeout=300)
            except Exception as exc:
                await db.rollback();scan=await db.get(NewsScan,sid,populate_existing=True)
                scan.state='interrupted';scan.finished_at=utcnow();scan.report=dict(scan.report,error='scan_timeout' if isinstance(exc,TimeoutError) else 'scan_internal_error',model_calls=0)
                await db.commit()
    finally:await redis.eval(RELEASE,1,SCAN_LOCK,token)

async def dispatch(now=None):
    """Free preparation, existing job execution and the existing global publication lock."""
    from app.research.executions import ACTIVE,prepare_job,allowance
    from app.research.worker import LOCK,RELEASE
    now=now or utcnow();redis=get_redis();token=secrets.token_hex(24).encode()
    if not await redis.set(LOCK,token,nx=True,ex=1800):return
    try:
        async with get_sessionmaker()() as db:
            control=await db.get(ResearchControl,1)
            if not control or not control.enabled or not control.rapid_enabled:return
            if await db.scalar(select(EditorialExecution.id).where(EditorialExecution.state.in_(ACTIVE)).limit(1)):return
            day=now.astimezone(MADRID).date();start=datetime.combine(day,datetime.min.time(),tzinfo=MADRID).astimezone(UTC)
            if await db.scalar(select(EditorialCandidate.id).join(Article,Article.id==EditorialCandidate.article_id).where(Article.status=='published',Article.published_at>=start).limit(1)):return
            config=settings()
            candidates=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='news',EditorialCandidate.state=='ready',EditorialCandidate.attempts==0,
                (EditorialCandidate.next_attempt_at.is_(None))|(EditorialCandidate.next_attempt_at<=now)).order_by(EditorialCandidate.created_at.desc()).limit(20))).all()
            for candidate in candidates:
                event=candidate.details.get('event')
                if not event or event['event'] not in {'launch','availability'}:continue
                key=f'rapid:{candidate.id}:{day}'
                if await db.scalar(select(EditorialExecution.id).where(EditorialExecution.request_key==key)):continue
                if not await allowance(db,config,day):
                    candidate.reason='budget_exhausted';candidate.next_attempt_at=datetime.combine(day+timedelta(days=1),datetime.min.time(),tzinfo=MADRID).astimezone(UTC);await db.commit();return
                job=EditorialExecution(request_key=key,mode='rapid',candidate_id=candidate.id);db.add(job);await db.commit()
                await prepare_job(db,job,config,now=now)
                if job.state=='awaiting_approval':
                    await confirm_job(db,job,now)
                elif job.reason=='budget_exhausted':
                    candidate.state='ready';candidate.reason='budget_exhausted';candidate.next_attempt_at=now+INTERVAL
                await db.commit();return
    finally:await redis.eval(RELEASE,1,LOCK,token)


async def confirm_job(db,job,now=None):
    from app.research.executions import allowance,prices
    now=now or utcnow();config=settings();day=now.astimezone(MADRID).date()
    control=await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update().execution_options(populate_existing=True))
    reason=None
    if not control or not control.enabled or not control.rapid_enabled:reason='rapid_disabled'
    elif job.prepared.get('day')!=str(day) or aware(job.expires_at)<now:reason='quote_expired'
    elif prices(config)!=job.prepared['prices']:reason='quote_changed'
    elif job.max_reserved_microusd>await allowance(db,config,day):reason='budget_exhausted'
    if reason:
        job.state='failed';job.reason=reason;job.finished_at=now
    else:
        job.state='queued';job.report=dict(job.report,trigger='corroborated_named_announcement',automatically_authorized=True)
        db.add(AuditLog(actor='automation',action='research_rapid_queued',entity_type='research',entity_id=job.id,details={'candidate_id':job.candidate_id,'maximum_microusd':job.max_reserved_microusd}))
    await db.commit()

async def loop():
    while True:
        try:
            await get_redis().set('foroia:research:news-heartbeat',utcnow().isoformat(),ex=90)
            await tick()
        except Exception:print(json.dumps({'event':'news_monitor_unavailable'}),flush=True)
        await asyncio.sleep(30)
