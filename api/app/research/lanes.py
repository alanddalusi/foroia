"""Independent workspaces for the existing coordinator, never another scheduler."""
import asyncio
import copy
import hashlib

from sqlalchemy import select, func, case

from app.models import EditorialCandidate, EditorialLaneRun, GenerationUsage, ResearchControl, utcnow
from app.research.writing import StopRun

FATAL = {'paused', 'lock_lost', 'reservation_accounting_mismatch', 'usage_outside_budget_bound'}
TERMINAL = {'published', 'skipped', 'draft', 'review'}


class LaneRun:
    """Use the existing pipeline/checkpoints while reserving only on the parent."""
    def __init__(self, lane, parent):
        object.__setattr__(self, 'lane', lane)
        object.__setattr__(self, 'budget_run', parent)

    @property
    def id(self): return self.budget_run.id
    @property
    def editorial_date(self): return self.budget_run.editorial_date
    @property
    def reserved_microusd(self): return self.budget_run.reserved_microusd
    def __getattr__(self, key): return getattr(self.lane, key)
    def __setattr__(self, key, value): setattr(self.lane, key, value)


async def claim(db, parent, engine, redis, token, slot=1):
    from app.research.worker import LOCK
    control = await db.scalar(select(ResearchControl).where(ResearchControl.id == 1).with_for_update())
    if not control or not control.enabled: raise StopRun('paused')
    if await redis.get(LOCK) != token: raise StopRun('lock_lost')
    row = await db.scalar(select(EditorialLaneRun).where(
        EditorialLaneRun.run_id == parent.id, EditorialLaneRun.engine == engine, EditorialLaneRun.slot==slot
    ).with_for_update().execution_options(populate_existing=True))
    if row is None:
        row = EditorialLaneRun(run_id=parent.id, engine=engine, slot=slot, report={})
        db.add(row)
        await db.flush()
    owner = hashlib.sha256(token).hexdigest()
    if row.status in TERMINAL or (row.status == 'running' and row.owner_hash == owner):
        await db.commit()
        return None
    row.status, row.owner_hash, row.finished_at = 'running', owner, None
    await db.commit()
    return LaneRun(row, parent)


async def practical_preflight(db, now, doc_loader, receipt_path, practical_slots=1):
    """Determine whether the protected headroom has a viable recipient, for free."""
    from app.research.queue import prepare_candidate, defer_or_reject
    from app.research.sources import SourceError
    from app.research.recovery import PENDING
    rows = (await db.scalars(select(EditorialCandidate).where(
        EditorialCandidate.engine == 'evergreen', EditorialCandidate.target_article_id.is_(None),
        EditorialCandidate.state.in_(PENDING),
        (EditorialCandidate.next_attempt_at.is_(None)) | (EditorialCandidate.next_attempt_at <= now)
    ).order_by(case((EditorialCandidate.state.in_(['publication_error','correction_pending','budget_pending']),0),else_=1),
        EditorialCandidate.priority.desc(), EditorialCandidate.created_at).limit(20))).all()
    errors = []
    for candidate in rows:
        try:
            if candidate.state=='publication_error':return candidate.id, errors
            if candidate.details.get('resume_report',{}).get('proposal'):
                from app.research.executions import resume_material
                await resume_material(db,candidate,now,receipt_path,doc_loader=doc_loader)
                return candidate.id,errors
            options = {'receipt_path': receipt_path,'practical_slots':practical_slots}
            if doc_loader: options['doc_loader'] = doc_loader
            await prepare_candidate(db, candidate, now, {'remaining': 4}, **options)
            return candidate.id, errors
        except (SourceError, StopRun) as exc:
            reason = exc.code if isinstance(exc, SourceError) else str(exc)
            errors.append({'candidate_id':candidate.id,'reason':reason,
                           'details':getattr(exc,'details',[]),'provider_calls':0})
            await defer_or_reject(db, candidate, reason, now)
    return None, errors


async def summarize(db, parent):
    rows = (await db.scalars(select(EditorialLaneRun).where(
        EditorialLaneRun.run_id == parent.id).order_by(EditorialLaneRun.id))).all()
    publications = [p for row in rows for p in row.report.get('publications', [])]
    planned=parent.report.get('planned_publications',2)
    costs=dict((await db.execute(select(EditorialCandidate.engine,func.sum(GenerationUsage.estimated_microusd))
        .select_from(GenerationUsage).outerjoin(EditorialCandidate,EditorialCandidate.id==GenerationUsage.candidate_id)
        .where(GenerationUsage.run_id==parent.id).group_by(EditorialCandidate.engine))).all())
    usage=(await db.scalars(select(GenerationUsage).where(GenerationUsage.run_id==parent.id))).all()
    def keys(report):
        result={e.get('ledger_key') for e in report.get('stage_checkpoints',{}).values()}
        for a in report.get('candidate_attempts',[]):result.update(keys(a.get('report') or {}))
        return result-{None}
    def lane_cost(row):
        identifiers=keys(row.report)
        return sum(u.estimated_microusd for u in usage if u.request_key in identifiers)
    parent.status = 'published' if publications else 'skipped'
    parent.reason = 'quality_checks_passed' if len(publications) == planned else 'partial_publication' if publications else 'no_verified_publication'
    parent.article_id = publications[-1]['article_id'] if publications else None
    parent.report = dict(parent.report, publications=publications,
        lanes=[{'engine':r.engine,'slot':r.slot,'status':r.status,'reason':r.reason,'article_id':r.article_id,
                'candidate_id':r.candidate_id,'reported_cost_microusd':lane_cost(r),
                'billing_verified':False} for r in rows],
        shared_research_reported_microusd=costs.get(None,0),
        planned_publications=planned, verified_publications=len(publications),
        lanes_complete=all(r.status in TERMINAL for r in rows) and len(rows)==planned)
    parent.finished_at = utcnow()
    await db.commit()


async def execute(db, parent, config, redis, token, *, news_collector, doc_loader=None,
                  generator=None, verifier=None, receipt_path=None):
    from app.research import editorial
    from app.research.queue import seed_evergreen, recover_verified_examples
    from app.research.event_sources import drafting_headroom
    await seed_evergreen(db)
    await recover_verified_examples(db,utcnow(),receipt_path)
    from app.research.recovery import recover_known_failures
    await recover_known_failures(db,utcnow())
    # Pin the plan to the day. Changing configuration never adds slots to a
    # previously started/completed day after restart.
    practical=parent.report.get('practical_slots',config.practical_publications)
    plan=[('news',1),*[('evergreen',slot) for slot in range(1,practical+1)]]
    parent.report = dict(parent.report, lanes_version=1, lanes_complete=False,
        practical_slots=practical,planned_publications=len(plan))
    await db.commit()
    prior = (await db.scalars(select(EditorialLaneRun).where(
        EditorialLaneRun.run_id == parent.id, EditorialLaneRun.engine == 'evergreen'))).all()
    remaining=practical-sum(r.status in TERMINAL for r in prior)
    protected = 0
    if remaining:
        try:
            candidate_id, errors = await asyncio.wait_for(practical_preflight(
                db, utcnow(), doc_loader, receipt_path,practical), timeout=90)
            parent.report = dict(parent.report, practical_preflight=errors)
            if candidate_id: protected = drafting_headroom(config)*remaining
        except (TimeoutError, OSError, ValueError):
            await db.rollback()
            await db.refresh(parent)
            parent.report = dict(parent.report, practical_preflight=[{'reason':'preflight_unavailable','provider_calls':0}])
    parent.report = dict(parent.report, practical_headroom_microusd=protected)
    await db.commit()
    unit=drafting_headroom(config)
    for engine,slot in plan:
        if engine=='evergreen':
            parent.report=dict(parent.report,practical_headroom_microusd=unit*max(0,practical-slot))
            await db.commit()
        workspace = await claim(db, parent, engine, redis, token,slot)
        if workspace is None: continue
        workspace_id=workspace.lane.id
        try:
            candidate=await db.get(EditorialCandidate,workspace.candidate_id) if workspace.candidate_id else None
            if candidate and candidate.state in {'needs_verification','published'}:
                from app.research.publication import verify_candidate
                await verify_candidate(db,candidate,verifier=verifier)
                workspace.status='published' if candidate.state=='published' else 'needs_verification' if candidate.state=='needs_verification' else 'skipped'
                workspace.reason='quality_checks_passed' if candidate.state=='published' else 'publication_verification_pending'
                if candidate.state=='published':
                    workspace.report=dict(workspace.report,publications=[{'candidate_id':candidate.id,
                        'article_id':candidate.article_id,'url':candidate.details['verification']['url']}])
                await db.commit()
                continue
            if candidate and candidate.state in {'generating','preparing'}:
                checkpoints=workspace.report.get('stage_checkpoints',{})
                uncertain=any(e.get('state') in {'calling','reserving','uncertain'} for e in checkpoints.values())
                if uncertain:
                    candidate.state='technical_error';candidate.reason='uncertain_provider_result'
                    workspace.status='skipped';workspace.reason='uncertain_provider_result'
                    await db.commit()
                    continue
                candidate.details=dict(candidate.details,resume_report=copy.deepcopy(workspace.report))
                candidate.state='deferred';candidate.next_attempt_at=utcnow()
                await db.commit()
            await asyncio.wait_for(editorial.execute(db, workspace, config, redis, token,
                news_collector=news_collector, doc_loader=doc_loader, generator=generator or editorial.generate,
                verifier=verifier, receipt_path=receipt_path, max_publications=1,
                _lane_engine=engine), timeout=360)
        except Exception as exc:
            await db.rollback()
            await db.refresh(parent)
            row = await db.get(EditorialLaneRun, workspace_id, populate_existing=True)
            reason = str(exc) if isinstance(exc, StopRun) else 'lane_timeout' if isinstance(exc, TimeoutError) else 'lane_internal_error'
            row.status, row.reason, row.finished_at = 'draft' if row.article_id else 'skipped', reason, utcnow()
            row.report=dict(row.report,failure={'code':reason,'details':exc.details if isinstance(exc,StopRun) else []})
            active=await db.get(EditorialCandidate,row.candidate_id) if row.candidate_id else None
            if active and active.state=='generating':
                uncertain=any(c.get('state') in {'calling','reserving','uncertain'} for c in row.report.get('stage_checkpoints',{}).values())
                active.details=dict(active.details,resume_report=copy.deepcopy(row.report))
                active.state='technical_error' if uncertain else 'deferred'
                active.reason='uncertain_provider_result' if uncertain else reason
                active.next_attempt_at=None if uncertain else utcnow()
            await db.commit()
            if reason in FATAL: raise
        if workspace.reason in FATAL: raise StopRun(workspace.reason)
    parent.report=dict(parent.report,practical_headroom_microusd=0)
    await summarize(db, parent)
