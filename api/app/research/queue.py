"""Persistent opportunities, preflight, retry bounds and independently available evergreen."""
import hashlib
from datetime import timedelta
from difflib import SequenceMatcher
import os

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Article,EditorialCandidate,AuditLog,utcnow
from app.research.blueprints import BLUEPRINTS,BY_KEY
from app.research.documents import official_document,aware
from app.research.examples import verified_example
from app.research.selection import select as select_topic
from app.research.sources import SourceError
from app.research.writing import normalize,StopRun


def fingerprint(value):return hashlib.sha256(value.encode()).hexdigest()


async def insert_once(db,**data):
    existing=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.fingerprint==data['fingerprint']))
    if existing:return existing
    row=EditorialCandidate(**data)
    try:
        async with db.begin_nested():db.add(row);await db.flush()
        await db.commit();return row
    except IntegrityError:
        return await db.scalar(select(EditorialCandidate).where(EditorialCandidate.fingerprint==data['fingerprint']))


async def seed_evergreen(db):
    for b in BLUEPRINTS:
        row=await insert_once(db,fingerprint=fingerprint('evergreen:v1:'+b.key),engine='evergreen',kind=b.kind,
            topic=b.topic,section=b.section,intent=b.intent,keyword=b.keyword,priority=80 if b.example else 65,
            state='queued',details={'blueprint':b.key,'demand_source':'editorial_hypothesis','sources':list(b.docs)})
        if row.attempts==0 and not row.article_id and not row.target_article_id and row.state in {'queued','ready','deferred'} and any(getattr(row,k)!=v for k,v in {'topic':b.topic,'intent':b.intent,'keyword':b.keyword}.items()):
            previous={k:getattr(row,k) for k in ['topic','intent','keyword']}
            row.topic,row.intent,row.keyword=b.topic,b.intent,b.keyword
            row.details=dict(row.details,queue_audit={'at':utcnow().isoformat(),'decision':'clarified_user_task','previous':previous})
            row.details.pop('opportunity',None)
        if not row.details.get('opportunity'):
            from app.research.opportunities import opportunity
            row.details=dict(row.details,opportunity=opportunity(row,[],utcnow()))
    await db.commit()


async def recover_verified_examples(db,now,receipt_path=None):
    """Reopen only a resolved receipt failure, retaining all paid attempt limits."""
    rows=(await db.scalars(select(EditorialCandidate).where(
        EditorialCandidate.engine=='evergreen',EditorialCandidate.reason=='example_not_verified',
        EditorialCandidate.state.in_(['deferred','rejected']),EditorialCandidate.attempts<2).limit(100))).all()
    count=0
    for row in rows:
        blueprint=BY_KEY.get(row.details.get('blueprint'))
        if not blueprint or not blueprint.example:continue
        example=verified_example(blueprint.example,receipt_path or os.environ.get('EDITORIAL_EXAMPLE_RECEIPT','/app/verified-examples.json'),now)
        if not example:continue
        previous={'state':row.state,'reason':row.reason,'preflight_failures':row.details.get('preflight_failures',0)}
        row.state='queued';row.reason='example_receipt_revalidated';row.next_attempt_at=None
        row.details=dict(row.details,preflight_failures=0,receipt_recovery={
            'at':now.isoformat(),'previous':previous,'example_sha256':example['sha256']})
        db.add(AuditLog(actor='automation',action='example_receipt_recovered',entity_type='editorial_candidate',entity_id=row.id,details=previous))
        count+=1
    await db.commit()
    return count


async def discover_document_opportunities(db,now):
    """Documentation supplies evidence, not an automatic list of article topics.

    Retain legacy proposals and their provenance, grouped under the existing
    concrete user task. Never alter published, attempted or active work.
    """
    rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='evergreen',
        EditorialCandidate.state.in_(['queued','ready','deferred']),EditorialCandidate.attempts==0,
        EditorialCandidate.article_id.is_(None),EditorialCandidate.target_article_id.is_(None)).limit(500))).all()
    changed=0
    for row in rows:
        if row.details.get('demand_source')!='official_document_section_hypothesis':continue
        url=row.details.get('focus',{}).get('url')
        parent=next((b for b in BLUEPRINTS if url in b.docs),None)
        target=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.fingerprint==fingerprint('evergreen:v1:'+parent.key))) if parent else None
        row.state='rejected';row.reason='documentation_topic_merged' if target else 'documentation_topic_not_actionable'
        row.details=dict(row.details,queue_audit={'at':now.isoformat(),'decision':row.reason,
            'original_topic':row.topic,'merged_into_candidate_id':target.id if target else None,
            'explanation':'El apartado se conserva como fuente; no es por sí solo una necesidad editorial distinta.'})
        changed+=1
    from app.research.opportunities import opportunity
    articles=(await db.execute(select(Article.id,Article.title,Article.slug,Article.summary).where(Article.status=='published').limit(500))).all()
    for row in rows:
        if row.state in {'queued','ready','deferred'} and row.details.get('blueprint') in BY_KEY:
            row.details=dict(row.details,opportunity=opportunity(row,articles,now))
    if rows:await db.commit()
    return changed


def focused_document(document,key):
    section=next((s for s in document.get('sections',[]) if s['key']==key),None)
    if not section:raise StopRun('documentation_section_missing')
    original=document['url'];url=original+('#'+section['anchor'] if section.get('anchor') else '')
    return {**{k:v for k,v in document.items() if k!='sections'},'url':url,
        'id':int(fingerprint(original+':'+key)[:12],16),'title':(document['title']+' — '+section['title'])[:200],
        'text':section['text'],'raw_document_url':original,'focus_key':key,'content_sha256':fingerprint(section['text'])}


def example_terms(example):
    """API names and SQL clauses the verified example actually relies on."""
    import re
    code=(example or {}).get('code','')
    terms={m.group(1) for m in re.finditer(r'\.([A-Za-z_][A-Za-z0-9_]{2,})\s*\(',code)}
    terms|={m.group(1) for m in re.finditer(r'^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)',code,re.M)}
    terms|={m.group(0) for m in re.finditer(r'\b(?:INSERT OR REPLACE|PRIMARY KEY|ON CONFLICT|NOT NULL|CREATE TABLE)\b',code)}
    return sorted(terms)


def example_focused(document,terms,limit=9000,window=1400):
    """Put the passages that document the verified example FIRST, then the opening.

    The evidence catalogue keeps 18,000 characters and the model sees roughly the first
    12,000 bytes per source. Run 15 explained casefold() while stdtypes.html only
    supplied its first 18,000 characters, so the reviewer correctly found no support.
    Exact substrings of the original page: quotes remain verifiable against it.
    """
    text=document['text']
    if len(text)<=limit or not terms:return document
    lowered=text.lower();spans=[]
    for term in terms:
        found=0;start=0
        while found<2:
            at=lowered.find(term.lower(),start)
            if at<0:break
            spans.append((max(0,at-window//3),min(len(text),at+window)));found+=1;start=at+len(term)
    spans.sort();merged=[]
    for a,b in spans:
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    parts=[];size=0
    for a,b in merged:
        piece=text[a:b]
        if size+len(piece)>limit:piece=piece[:max(0,limit-size)]
        if len(piece)>=200:parts.append(piece);size+=len(piece)
        if size>=limit:break
    if size<limit:parts.append(text[:limit-size])
    focused='\n\n'.join(parts)
    return {**document,'text':focused,'raw_document_url':document.get('raw_document_url',document['url']),
            'focus_terms':[t for t in terms if t.lower() in focused.lower()],'content_sha256':fingerprint(focused)}


async def discover_news(db,documents,stats,now):
    selected,report=select_topic(documents)
    by_id={s['id']:s for s in documents}
    for group in report['candidates']:
        evidence=[by_id[i] for i in group['source_ids']]
        from app.research.events import identify
        event=identify(evidence[0]) if evidence else None
        if event:
            await upsert_event(db,evidence,event,now)
            continue
        evidence,assessment=select_topic(evidence)
        valid=bool(evidence)
        await insert_once(db,fingerprint=fingerprint('news:'+group['topic_id']),engine='news',kind='news',
            topic=group['title'],section='actualidad',intent='Entender qué cambia, para quién y con qué evidencia.',
            keyword=group['title'][:150],priority=90,state='ready' if valid else 'rejected',
            reason='' if valid else group['reason'],
            details={'sources':evidence,'selection':assessment,'discovered_at':now.isoformat(),'demand_source':'official_feed'})
    return report


async def upsert_event(db,documents,event,now):
    """Shared by daytime and nightly discovery; identity never depends on RSS order."""
    from app.research.events import compatible,event_key,identify
    from app.models import ResearchControl
    await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='news').order_by(EditorialCandidate.id.desc()).limit(500))).all()
    matches=[r for r in rows if compatible(r.details.get('event'),event)]
    if len(matches)>1:raise StopRun('ambiguous_event_identity')
    prior=matches[0] if matches else None
    if prior and (prior.attempts or prior.state in {'published','generating','needs_verification'} or
        (prior.state=='rejected' and prior.reason not in {'waiting_independent_sources','insufficient_independent_topic_sources'})):return prior
    all_docs={}
    for source in ((prior.details.get('sources',[]) if prior else [])+documents):
        if not compatible(identify(source),event):continue
        old=all_docs.get(source['url'])
        if old and old.get('organization_verified') and len(old.get('text',''))>=500 and not (source.get('organization_verified') and len(source.get('text',''))>=500):continue
        all_docs[source['url']]=source
    from app.research.selection import organization
    ordered=list(all_docs.values());representatives={}
    for source in ordered:
        if (org:=organization(source)) and org not in representatives:representatives[org]=source
    first=list(representatives.values())
    merged=(first+[s for s in ordered if s not in first])[:8]
    selected,assessment=select_topic(merged)
    waiting='waiting_independent_sources' if any(organization(s) and len(s.get('text',''))>=500 for s in merged) else 'waiting_verified_sources'
    details=dict(prior.details if prior else {},event=prior.details['event'] if prior else event,sources=merged,selection=assessment,
        demand_source='official_announcement',discovered_at=(prior.details.get('discovered_at') if prior else None) or now.isoformat(),
        decision={'relevance':event['category'],'novelty':'new_named_event','impact':event['event'],
            'evidence_organizations':assessment['selected_organizations'],'reason':('verified_official_announcement' if assessment.get('verification_mode')=='official_announcement' else 'corroborated_named_event') if selected else waiting})
    if prior:
        prior.details=details;prior.state='ready' if selected else 'queued';prior.reason='' if selected else waiting
        await db.commit();return prior
    return await insert_once(db,fingerprint=event_key(event),engine='news',kind='news',topic=documents[0]['title'][:200],section='actualidad',
        intent='Entender el acontecimiento, su procedencia y los límites de la evidencia disponible.',keyword=documents[0]['title'][:150],
        priority=90,state='ready' if selected else 'queued',reason='' if selected else waiting,details=details)


async def prepare_candidate(db,candidate,now,fetch_budget,doc_loader=official_document,receipt_path=None,practical_slots=1):
    if candidate.attempts>=2:raise StopRun('candidate_attempt_limit')
    if not candidate.target_article_id and candidate.details.get('demand_source')=='official_document_section_hypothesis':
        raise StopRun('documentation_topic_not_actionable')
    existing=(await db.execute(select(Article.id,Article.title).where(Article.status=='published').limit(500))).all()
    from app.research.opportunities import opportunity
    related=(await db.execute(select(Article.id,Article.title,Article.slug,Article.summary).where(Article.status=='published').limit(500))).all()
    candidate.details=dict(candidate.details,opportunity=opportunity(candidate,related,now))
    await db.commit()
    if not candidate.target_article_id and any(SequenceMatcher(None,normalize(candidate.topic),normalize(a.title)).ratio()>=.78 for a in existing):
        raise StopRun('duplicate_topic')
    published_topics=(await db.scalars(select(EditorialCandidate.topic).where(EditorialCandidate.state=='published').limit(500))).all()
    if not candidate.target_article_id and any(SequenceMatcher(None,normalize(candidate.topic),normalize(t)).ratio()>=.78 for t in published_topics):
        raise StopRun('duplicate_topic')
    if candidate.engine=='news':
        documents=candidate.details.get('sources',[])
        # Stale news is not resurrected by a restart or a long queue.
        from datetime import datetime
        if any(not s.get('published') or now-aware(datetime.fromisoformat(s['published']))>timedelta(hours=48) for s in documents):
            raise StopRun('stale_sources')
        chosen,report=select_topic(documents)
        if not chosen:raise StopRun('insufficient_independent_topic_sources')
        candidate.details=dict(candidate.details,selection=report,opportunity=opportunity(candidate,related,now,verified=True));await db.commit()
        from app.research.editorial_policy import policy_for
        return chosen,{'kind':'news',**policy_for(chosen),'candidate_id':candidate.id,'selection':report,'editorial_opportunity':candidate.details['opportunity']}
    from app.research.blueprints import AI_APPLICATIONS
    parent=BY_KEY.get(candidate.details.get('blueprint'))
    if not parent and candidate.details.get('focus'):
        parent=next((b for b in BLUEPRINTS if candidate.details['focus']['url'] in b.docs),None)
    application=AI_APPLICATIONS.get(parent.key if parent else '')
    if not application:raise StopRun('evergreen_missing_ai_application')
    if not candidate.target_article_id and any(w in normalize(candidate.topic) for w in ['json','csv','python','sqlite','pydantic','fastapi','unicode']):
        recent=(await db.execute(select(EditorialCandidate.topic,EditorialCandidate.published_at).join(Article,Article.id==EditorialCandidate.article_id)
            .where(EditorialCandidate.engine=='evergreen',EditorialCandidate.state=='published',Article.status=='published',
                EditorialCandidate.target_article_id.is_(None),EditorialCandidate.published_at>=now-timedelta(days=7))
            .order_by(EditorialCandidate.published_at.desc()).limit(100))).all()
        technical=[r for r in recent if any(w in normalize(r.topic) for w in ['json','csv','python','sqlite','pydantic','fastapi','unicode'])]
        if len(technical)>=2 and practical_slots<2:
            candidate.details=dict(candidate.details,evergreen_cooldown_until=(aware(technical[1].published_at)+timedelta(days=7)).isoformat())
            await db.commit();raise StopRun('evergreen_topic_cooldown')
    blueprint=BY_KEY.get(candidate.details.get('blueprint'))
    focus=candidate.details.get('focus')
    if focus:
        from types import SimpleNamespace
        blueprint=SimpleNamespace(docs=(focus['url'],),example=None,kind='guide')
    if not blueprint:raise StopRun('unknown_blueprint')
    example=None
    if blueprint.example:
        path=receipt_path or os.environ.get('EDITORIAL_EXAMPLE_RECEIPT','/app/verified-examples.json')
        example=verified_example(blueprint.example,path,now)
        if not example:
            from app.research.examples import receipt_status
            raise StopRun('example_not_verified',[{'example_id':blueprint.example,'reason':receipt_status(blueprint.example,path,now)}])
    documents=[]
    terms=example_terms(example) if example else []
    for url in blueprint.docs:
        document=await doc_loader(db,url,now,fetch_budget)
        document=focused_document(document,focus['key']) if focus else {k:v for k,v in document.items() if k!='sections'}
        documents.append(example_focused(document,terms) if terms and not focus else document)
    min_orgs=2 if blueprint.kind=='comparison' else 1
    if len({s['organization'] for s in documents if s.get('organization_verified') and s.get('kind')=='official_documentation'})<min_orgs:
        raise StopRun('insufficient_official_documentation')
    # Do not apply the news-only two-publisher gate to authoritative documentation.
    policy={'kind':blueprint.kind,'min_organizations':min_orgs,'candidate_id':candidate.id,'ai_application':application,'numeric_citation_version':2,
        'topic':candidate.topic,'intent':candidate.intent,'keyword':candidate.keyword,'section':candidate.section,
        'example':example,'external_testing':('El ejemplo de código se ha ejecutado en un entorno aislado; no se ha probado la interfaz ni ningún servicio externo.'
            if example else 'El contenido se ha contrastado con la documentación oficial citada; no se ha probado la interfaz ni ningún servicio externo.')}
    policy['editorial_opportunity']=opportunity(candidate,related,now,verified=True)
    if candidate.target_article_id:
        if not candidate.details.get('previous_evidence_quotes'):raise StopRun('update_missing_previous_evidence')
        policy.update(operation='update',previous_body=candidate.details['target_snapshot']['body'][:16000],
            previous_evidence_quotes=candidate.details['previous_evidence_quotes'],max_operation_microusd=60000)
    candidate.details=dict(candidate.details,evidence=documents,prepared_at=now.isoformat(),policy={k:v for k,v in policy.items() if k!='example'})
    candidate.details=dict(candidate.details,opportunity=opportunity(candidate,related,now,verified=True))
    candidate.state='ready';candidate.reason='';candidate.next_attempt_at=None;await db.commit()
    return documents,policy


async def defer_or_reject(db,candidate,reason,now):
    from app.research.recovery import CORRECTABLE, TECHNICAL
    if reason=='document_fetch_budget':
        # Shared retrieval capacity is not a failure of this candidate. Never
        # turn three budget deferrals into a permanent content rejection.
        candidate.state='deferred';candidate.reason=reason;candidate.next_attempt_at=now+timedelta(hours=6)
        await db.commit();return
    if reason=='evergreen_topic_cooldown':
        from datetime import datetime
        candidate.state='deferred';candidate.reason=reason
        candidate.next_attempt_at=datetime.fromisoformat(candidate.details['evergreen_cooldown_until'])
        await db.commit();return
    if reason=='budget_exhausted':
        candidate.state='budget_pending';candidate.reason=reason
        candidate.next_attempt_at=now+timedelta(hours=6)
        await db.commit();return
    if reason in {'publication_check_failed','publication_verification_pending'}:
        candidate.state='publication_error';candidate.reason=reason
        candidate.next_attempt_at=now+timedelta(hours=6)
        await db.commit();return
    if reason in CORRECTABLE:
        saved=candidate.details.get('resume_report') or {}
        candidate.state='correction_pending' if (saved.get('proposal') or saved.get('stage_checkpoints')) and int(saved.get('corrections_used',0))<2 else 'rejected'
        candidate.reason=reason
        candidate.next_attempt_at=now+timedelta(hours=6) if candidate.state=='correction_pending' else None
        if candidate.state=='correction_pending':
            saved=dict(saved,resume_correction=True,recovery_correction_limit=2)
            candidate.details=dict(candidate.details,resume_report=saved)
        await db.commit();return
    if reason in TECHNICAL:
        candidate.state='technical_error';candidate.reason=reason;candidate.next_attempt_at=None
        await db.commit();return
    transient=reason in {'document_unavailable','http_status','document_fetch_budget','short_document',
        'example_not_verified','provider_unavailable','incomplete_generation','budget_exhausted','review_rejected','document_fetch_budget','maintenance_budget_exhausted'}
    failures=int(candidate.details.get('preflight_failures',0))+1
    candidate.details=dict(candidate.details,preflight_failures=failures)
    candidate.reason=reason
    candidate.state='deferred' if transient and failures<3 and candidate.attempts<2 else 'rejected'
    candidate.next_attempt_at=now+timedelta(hours=6) if candidate.state=='deferred' else None
    await db.commit()
