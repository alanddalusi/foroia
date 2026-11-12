"""Bounded evidence recovery for the existing nightly coordinator, before drafting."""
import asyncio
import hashlib
import http.client
import time
from datetime import datetime,timedelta
from urllib.parse import urlsplit
from sqlalchemy import select
from app.models import Article,EditorialCandidate
from app.research import sources
from app.research.selection import select as select_topic,PUBLISHERS,organization
from app.research.news_gate import matches,initial_filing_key,retrieval_hint
from app.research import event_sources

OFFICIAL=event_sources.OFFICIAL
ERRORS=(sources.SourceError,OSError,ValueError,TimeoutError,http.client.HTTPException)

def reason_for(exc):
    code=getattr(exc,'code','network_error')
    if code in {'domain_not_allowed','official_path_not_allowed','unsafe_url'}:return code
    if code in {'date_unverifiable','document_stale','index_without_article','document_unrelated','unverified_organization','already_published'}:return code
    if code in {'document_fetch_budget','index_fetch_budget','phase_fetch_budget','recovery_timeout'}:return 'recovery_limit_reached'
    if code=='short_document':return 'insufficient_document_content'
    return 'document_inaccessible'


async def discover(db,run,config,redis,token,now,provider=None,fetcher=None,recovery_feeds=None,research_fn=None,
                   alternative_provider=None,official_indexes=None,time_budget_seconds=240):
    from app.research.queue import discover_news
    nominations,report=await research_fn(db,run,config,redis,token,now,provider)
    fetcher=fetcher or sources.fetch
    errors=[];cache={};documents={};indices={};index_dates={};expansions=[];recoveries=[];decisions=[];selections=[]
    counts={'article':0,'index':0,'feed':0};feed_rows=None
    deadline=time.monotonic()+max(0,min(time_budget_seconds,300))
    searches=[];index_queries=set();candidate_material={}
    phase='free'
    published=(await db.scalars(select(Article).where(Article.status=='published'))).all()
    used_urls={s['url'].split('?')[0].rstrip('/') for a in published for s in a.sources}
    recent_filings={initial_filing_key(a.title):a.slug for a in published if a.published_at and
        a.published_at.replace(tzinfo=now.tzinfo)>=now-timedelta(days=7) and initial_filing_key(a.title)}

    def failure(url,stage,exc,target=None):
        row={'url':str(url)[:2000],'stage':stage,'code':getattr(exc,'code','network_error'),
            'reason':reason_for(exc),'http_status':getattr(exc,'http_status',None)}
        if getattr(exc,'relation',None):row['correspondence']=exc.relation
        if getattr(exc,'source_date',None):row['source_date']=exc.source_date
        if target is not None:row['candidate_index']=target
        errors.append(row);return row

    async def load(value,kind='article'):
        url=sources.canonical(value)
        if url in cache:
            old=cache[url]
            if isinstance(old,Exception):raise old
            return old
        if time.monotonic()>=deadline:raise sources.SourceError('Tiempo de recuperación agotado','recovery_timeout')
        if kind=='article' and phase=='free' and counts[kind]>=14:
            raise sources.SourceError('Se conservan descargas para la búsqueda alternativa','phase_fetch_budget')
        limit={'article':20,'index':5,'feed':11}[kind]
        if counts[kind]>=limit:raise sources.SourceError('Límite de recuperación', 'index_fetch_budget' if kind=='index' else 'document_fetch_budget')
        counts[kind]+=1
        try:
            final,raw=await asyncio.wait_for(asyncio.to_thread(fetcher,url,sources.MAX_BYTES),15)
            final=sources.canonical(final)  # injected transports obey the same destination policy
            if len(raw)>sources.MAX_BYTES:raise sources.SourceError('Documento demasiado grande','source_too_large')
            cache[url]=(final,raw)
        except ERRORS as exc:cache[url]=exc;raise
        return cache[url]

    async def resolve(value,item):
        url=sources.canonical(value)
        final,raw=await load(url,'index' if sources.is_news_index(url) else 'article')
        if not sources.is_news_index(final,raw):return [(final,raw)]
        if url not in indices:indices[url]=sources.news_links(raw,final,True)
        links=indices[url]
        # SEC attachment filenames are not headlines. Actual retrieved contents
        # must still pass issuer, event and date checks below.
        sec=urlsplit(final).hostname in {'sec.gov','www.sec.gov'}
        related=[r for r in links if (sec and not urlsplit(r['url']).path.rsplit('/',1)[-1].lower().startswith(('exhibit','ex-','ex_'))) or
            (not sec and retrieval_hint(item,r['title']))]
        ranked=sorted(related,key=lambda r:(-retrieval_hint(item,r['title']),-len(set(item.title.lower().split()) & set(r['title'].lower().split()))))[:4]
        expansions.append({'candidate_title':item.title,'index_url':url,'discovered_links':len(links),
            'related_links':len(related),'article_urls':[r['url'] for r in ranked]})
        if not ranked:raise sources.SourceError('Índice sin artículo individual relacionado','index_without_article')
        result=[]
        for row in ranked:
            if row.get('published'):index_dates[row['url']]={**row,'index_url':url}
            try:
                final_article,page=await load(row['url'])
                if sources.is_news_index(final_article,page):raise sources.SourceError('Otro índice','index_without_article')
                result.append((final_article,page))
            except ERRORS as exc:failure(row['url'],'index_article',exc)
        if not result:raise sources.SourceError('Índice sin artículo individual accesible','index_without_article')
        return result

    def document(final,raw,item,row=None):
        if final.split('?')[0].rstrip('/') in used_urls:raise sources.SourceError('Fuente ya publicada','already_published')
        title=sources.page_title(raw)
        text=sources.article_plain(raw)
        if urlsplit(final).hostname in {'sec.gov','www.sec.gov'} and not title:
            title=sources.sec_title(final,text)
        doc={'id':int(hashlib.sha256(final.encode()).hexdigest()[:12],16),'url':final,
            'title':title or (row or {}).get('title','Documento de la fuente'),'text':text,
            'language':'en','retrieved_at':now.isoformat(),'retrieval_method':'page',
            'content_origin':sources.content_origin(final,raw),**sources.source_attribution(final,raw,'unverified')}
        relation=matches(item,doc)
        if not relation['related']:
            exc=sources.SourceError('Documento sobre otro acontecimiento','document_unrelated');exc.relation=relation;raise exc
        stamp,precision=sources.publication_stamp(raw,final)
        indexed=index_dates.get(final)
        if not stamp and indexed and len(set(title.lower().split()) & set(indexed['title'].lower().split()))>=2:
            stamp=datetime.fromisoformat(indexed['published']);precision='publisher_index_calendar_day'
        if not stamp and row and row.get('rss_text') and row.get('published'):
            stamp=datetime.fromisoformat(row['published']);precision='rss_pubdate';doc['retrieval_method']='rss_full_content'
        if not stamp:raise sources.SourceError('No hay fecha original verificable','date_unverifiable')
        # A publisher's calendar date does not assert a midnight publication
        # time. Compare calendar days at the boundary instead of inventing one.
        calendar_day=precision in {'calendar_day','publisher_index_calendar_day','sec_filing_calendar_day'}
        timely=((now-timedelta(hours=48)).date()<=stamp.date()<=now.date()) if calendar_day else now-timedelta(hours=48)<=stamp<=now+timedelta(minutes=5)
        if not timely:
            exc=sources.SourceError('Documento fuera de la ventana','document_stale');exc.source_date=stamp.isoformat();raise exc
        if len(text)<500:raise sources.SourceError('Documento insuficiente','short_document')
        if not organization(doc):raise sources.SourceError('Autoría no verificada','unverified_organization')
        from app.modules.articles.media import official_videos
        doc.update(published=stamp.isoformat(),published_precision=precision,publication_index=(indexed or {}).get('index_url'),
            references=[r['url'] for r in sources.news_links(raw,final)],official_videos=official_videos(raw,final),event_correspondence=relation,
            content_sha256=hashlib.sha256(text.encode()).hexdigest())
        doc['evidence_role']='official_statement' if organization(doc) in OFFICIAL else 'independent_reporting'
        doc['announcement_scope']=item.title+' '+item.event
        from app.research.editorial_policy import official_source
        doc['corroboration_required']=not official_source(doc)
        documents[final]=doc;return doc

    async def feeds():
        nonlocal feed_rows
        if feed_rows is not None:return feed_rows
        feed_rows=[]
        allowed=recovery_feeds if recovery_feeds is not None else sources.INDEPENDENT_FEEDS+tuple(f for f in sources.FEEDS if f.organization!='unverified_scientific_authors')+sources.RAPID_FEEDS
        for feed in allowed[:11]:
            try:
                final,raw=await load(feed.url,'feed')
                if feed.kind=='html':rows=sources.news_links(raw,final,True)
                else:rows=sources.parse_feed(raw,feed,now)
                feed_rows.extend(dict(r,organization=feed.organization,feed_url=feed.url) for r in rows)
            except (*ERRORS,sources.ElementTree.ParseError) as exc:failure(feed.url,'related_feed',exc)
        return feed_rows

    async def related(item,accepted,number):
        rows=[]
        urls=(official_indexes(item) if callable(official_indexes) else official_indexes if official_indexes is not None else
            event_sources.entrypoints(item) if recovery_feeds is None else [])
        for url in urls[:3]:
            key=(event_sources.event_id(item),url)
            if key in index_queries:continue
            index_queries.add(key)
            search={'candidate_index':number,'event_id':key[0],'query':event_sources.query(item),
                'method':'official_index_local_query','index_url':url,'found_urls':[]}
            try:
                final,raw=await load(url,'index')
                found=sources.news_links(raw,final,True)
                matching=[r for r in found if retrieval_hint(item,r['title'])]
                for row in matching:
                    if row.get('published'):index_dates[row['url']]={**row,'index_url':url}
                rows.extend(matching)
                search.update(status='completed',found_urls=[r['url'] for r in matching][:20],matching_links=len(matching))
            except ERRORS as exc:
                failure(url,'official_index',exc,number)
                search.update(status='failed',reason=reason_for(exc),code=getattr(exc,'code','network_error'))
            searches.append(search)
        rows.extend(await feeds())
        known=[u for slot in ('web_research','alternative_web_research') for u in
            (run.report.get(slot,{}).get('usage',{}).get('_web',{}).get('sources') or [])]
        for value in [*known,*[u for d in accepted for u in d.get('references',[])]]:
            try:
                url=sources.canonical(value)
                if sources.is_news_index(url):
                    # Reuse raw index links, ranked anew for this candidate.
                    final,raw=await load(url,'index')
                    rows.extend(sources.news_links(raw,final,True));continue
                rows.append({'url':url,'title':urlsplit(url).path.replace('/',' ').replace('-',' ')})
            except ERRORS as exc:failure(value,'related_reference',exc)
        unique={}
        for row in rows:
            old=unique.get(row['url'])
            if old is None or len(row['title'])>len(old['title']):unique[row['url']]=row
        for doc in documents.values():
            unique.setdefault(doc['url'],{'url':doc['url'],'title':doc['title']})
        accepted_urls={d['url'] for d in accepted}
        eligible=[r for r in unique.values() if not isinstance(cache.get(r['url']),Exception) and r['url'] not in accepted_urls and r['url'].split('?')[0].rstrip('/') not in used_urls
            and retrieval_hint(item,r['title'])]
        orgs={organization(d) for d in accepted}
        def rank(r):
            org=PUBLISHERS.get(urlsplit(r['url']).hostname) or sources.NEWS_HOSTS.get(urlsplit(r['url']).hostname)
            # Relevant original + independent publisher before another same-owner item.
            original_needed=not any(organization(d) in OFFICIAL for d in accepted)
            return (-retrieval_hint(item,r['title']),org in orgs,not(original_needed and org in OFFICIAL),-len(set(item.title.lower().split()) & set(r['title'].lower().split())))
        return sorted(eligible,key=rank)[:4]

    async def enqueue(item,chosen,decision):
        selections.append(await discover_news(db,chosen,{},now))
        urls={d['url'] for d in chosen}
        rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='news',EditorialCandidate.state.not_in(['published','rejected']))
            .order_by(EditorialCandidate.id.desc()).limit(100))).all()
        for row in rows:
            if urls & {d['url'] for d in row.details.get('sources',[])}:
                row.details=dict(row.details,web_opportunity=item.model_dump(),
                    demand_source='official_feed' if decision.get('origin')=='official_feed' else 'nightly_web_search')
                row.priority={'major_release':95,'practical_update':90,'research':85}[item.relevance];decision['candidate_ids'].append(row.id)
        await db.commit()
        decision['reason_for_decision']='verified_queued' if decision['candidate_ids'] else 'already_published'

    def rejection(accepted,diagnostics,number):
        if accepted:return 'independent_corroboration_missing'
        # An alternative can match the event but fail its date/provenance gate.
        # Report that substantive rejection instead of blaming the first URL.
        substantive=[r['reason'] for r in diagnostics if r.get('candidate_index')==number and r['reason'] in
            {'date_unverifiable','document_stale','unverified_organization','insufficient_document_content'}]
        if substantive:return substantive[0]
        primary=[r['reason'] for r in diagnostics if r['stage']=='primary_source' and r.get('candidate_index')==number]
        reasons=primary or [r['reason'] for r in diagnostics if r.get('candidate_index')==number or r['stage']=='index_article']
        return next((code for code in ['already_published','domain_not_allowed','official_path_not_allowed','unsafe_url',
            'index_without_article','document_unrelated','document_inaccessible','recovery_limit_reached'] if code in reasons),'independent_corroboration_missing')

    async def feed_opportunities():
        # Already bounded/cached RSS collection, not a second researcher or an
        # assertion that a model's blocked URL was verified. Every row goes
        # through the exact same document/event/date/publication gate below.
        from app.research.events import identify
        from app.research.night_web import NewsOpportunity
        # Only reuse feeds already consulted for the nominated event. An empty
        # or failed provider reply must not trigger a new batch of network IO.
        if feed_rows is None:return []
        result=[]
        known={event_sources.event_id(i) for i in nominations}
        for row in await feeds():
            org=row.get('organization')
            if org not in OFFICIAL or not row.get('published') or sources.is_news_index(row['url']):continue
            try:
                stamp=datetime.fromisoformat(row['published'].replace('Z','+00:00'))
                if stamp.tzinfo is None or not now-timedelta(hours=48)<=stamp<=now+timedelta(minutes=5):continue
                if row['url'].split('?')[0].rstrip('/') in used_urls:continue
                event=identify(row)
                if not event or event['entity']!=org:continue
                item=NewsOpportunity(title=row['title'][:200],event=row['title'][:600],date=event['date'],organization=org,
                    relevance='practical_update',reason='Anuncio concreto encontrado en el canal oficial; pendiente de verificar el documento original.',urls=[row['url']])
            except (ValueError,KeyError,TypeError):continue
            eid=event_sources.event_id(item)
            if eid in known:continue
            known.add(eid);result.append(item)
            if len(result)==3:break
        return result

    ordered=sorted(nominations,key=lambda n:{'major_release':0,'practical_update':1,'research':2}[n.relevance])
    feed_ids=set();feed_fallback_used=False
    if not ordered:
        extra=await feed_opportunities();ordered.extend(extra)
        feed_ids.update(event_sources.event_id(i) for i in extra);feed_fallback_used=True
    for number,item in enumerate(ordered):
        origin='official_feed' if event_sources.event_id(item) in feed_ids else 'web_search'
        start=len(errors);accepted=[];decision={**item.model_dump(),'candidate_ids':[],'origin':origin}
        duplicate=recent_filings.get(initial_filing_key(item.title+' '+item.event))
        if duplicate:
            decision.update(reason_for_decision='already_published',existing_url='/articulos/'+duplicate,diagnostics=[])
            decisions.append(decision);continue
        for value in item.urls:
            try:
                for final,raw in await resolve(value,item):
                    try:accepted.append(document(final,raw,item))
                    except ERRORS as exc:failure(final,'article_validation',exc,number)
            except ERRORS as exc:failure(value,'primary_source',exc,number)
        chosen,assessment=select_topic(accepted)
        if not chosen:
            for row in await related(item,accepted,number):
                try:
                    final,raw=await load(row['url'])
                    accepted.append(document(final,raw,item,row))
                    chosen,assessment=select_topic(accepted)
                    recoveries.append({'candidate_index':number,'url':row['url'],'reason':'recovered_corroboration' if chosen else 'independent_corroboration_missing'})
                    if chosen:break
                except ERRORS as exc:failure(row['url'],'related_article',exc,number)
        decision.update(verification=assessment,diagnostics=errors[start:],verified_source_urls=[d['url'] for d in accepted])
        if not chosen:
            decision['reason_for_decision']=rejection(accepted,errors[start:],number)
        elif not any(organization(d) in OFFICIAL for d in chosen):decision['reason_for_decision']='missing_original_source'
        else:
            await enqueue(item,chosen,decision)
        decision['event_id']=event_sources.event_id(item)
        decision['queries']=event_sources.plan(item)
        candidate_material[event_sources.event_id(item)]=(number,item,accepted,decision)
        decisions.append(decision)

        if number==len(ordered)-1 and not feed_fallback_used and not any(d['reason_for_decision']=='verified_queued' for d in decisions):
            extra=await feed_opportunities();ordered.extend(extra)
            feed_ids.update(event_sources.event_id(i) for i in extra);feed_fallback_used=True

    # Exhaust free event-focused retrieval first, for every candidate. A viable
    # free result prevents spending on a second discovery call just for variety.
    alternative_report={'state':'not_needed'}
    targets=[item for _,item,_,decision in candidate_material.values() if decision['reason_for_decision'] not in {'already_published','verified_queued'}][:3]
    if targets and not any(d['reason_for_decision']=='verified_queued' for d in decisions):
        if report.get('observed_tool_limit_exceeded'):
            alternative_report={'state':'skipped','reason':'search_tool_limit_exceeded'}
        elif time.monotonic()+95>=deadline:alternative_report={'state':'skipped','reason':'recovery_timeout'}
        elif not (alternative_provider or config.api_key.get_secret_value() or run.report.get('alternative_web_research')):
            alternative_report={'state':'skipped','reason':'recovery_not_configured'}
        else:
            phase='alternative'
            alternatives,alternative_report=await event_sources.search(db,run,config,redis,token,now,targets,alternative_provider)
            searches.append({'method':'openai_event_search','status':alternative_report.get('state'),
                'queries':[event_sources.plan(i) for i in targets],
                'search_calls':alternative_report.get('search_calls',0),
                'reason':alternative_report.get('reason'),'returned_candidates':len(alternatives),
                'maximum_microusd':alternative_report.get('reserved_microusd',alternative_report.get('maximum_microusd',0)),
                'accounted_microusd':alternative_report.get('accounted_microusd'),
                'actual_queries':[q for t in run.report.get('alternative_web_research',{}).get('usage',{}).get('_web',{}).get('tool_calls',[]) for q in t.get('queries',[])]})
            allowed={event_sources.event_id(i) for i in targets}
            handled=set()
            for alternative in alternatives:
                eid=event_sources.event_id(alternative)
                if eid not in allowed or eid in handled:
                    searches.append({'method':'openai_event_search_result','status':'rejected','reason':'unrequested_event','title':alternative.title})
                    continue
                handled.add(eid)
                number,item,accepted,decision=candidate_material[eid]
                start=len(errors);previous=decision['reason_for_decision']
                # Keep the nominated event immutable. Only these discovered URLs
                # may change; they pass exactly the same document gate.
                for value in alternative.urls:
                    if value in {d['url'] for d in accepted}:continue
                    try:
                        for final,raw in await resolve(value,item):
                            try:accepted.append(document(final,raw,item))
                            except ERRORS as exc:failure(final,'alternative_validation',exc,number)
                    except ERRORS as exc:failure(value,'alternative_source',exc,number)
                chosen,assessment=select_topic(accepted)
                if not chosen:
                    for row in await related(item,accepted,number):
                        try:
                            final,raw=await load(row['url']);accepted.append(document(final,raw,item,row))
                            chosen,assessment=select_topic(accepted)
                            if chosen:break
                        except ERRORS as exc:failure(row['url'],'alternative_related',exc,number)
                decision.update(initial_reason=previous,verification=assessment,
                    diagnostics=[*decision['diagnostics'],*errors[start:]],
                    verified_source_urls=list(dict.fromkeys(d['url'] for d in accepted)),
                    alternative_urls=alternative.urls)
                if chosen and any(organization(d) in OFFICIAL for d in chosen):await enqueue(item,chosen,decision)
                else:decision['reason_for_decision']=rejection(accepted,decision['diagnostics'],number)
    verified=sum(d['reason_for_decision']=='verified_queued' for d in decisions)
    report=dict(report,verification_status='verified_candidates' if verified else 'no_verified_candidates',verified_candidates=verified)
    return {'web':report,'opportunities':decisions,'selection':selections,'related_recovery':recoveries,'index_expansion':expansions,
        'document_snapshots':list(documents.values()),'recovery_version':3,
        'event_searches':searches,'alternative_research':alternative_report,
        'limits':{'article_fetches':20,'free_article_fetches':14,'index_fetches':5,'feed_fetches':11,'alternative_calls':1,
            'time_budget_seconds':max(0,min(time_budget_seconds,300))},
        'statistics':{'candidate_count':len(ordered),'web_candidate_count':len(nominations),'official_feed_candidate_count':len(feed_ids),
            'documents':len(documents),'fetch_failures':len(errors),'fetch_errors':errors,
            'fetch_counts':counts,'generation_calls_avoided':len(ordered)-verified}}
