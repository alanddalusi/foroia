"""Bounded recovery within the existing queue, checkpoints and budget ledger."""
import copy
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import Article, AuditLog, EditorialCandidate, EditorialExecution, EditorialLaneRun, ResearchRun
from app.research.documents import aware
from app.research.writing import StopRun

PENDING = ('queued', 'ready', 'deferred', 'correction_pending', 'budget_pending', 'publication_error')
CORRECTABLE = frozenset({'editorial_style_rejected', 'editorial_review_rejected', 'review_rejected',
    'official_attribution_missing', 'official_scope_requires_corroboration', 'invalid_example',
    'invalid_evidence', 'insufficient_content', 'unsupported_number', 'unsafe_format', 'invalid_article'})
TECHNICAL = frozenset({'uncertain_provider_result', 'interrupted_uncertain_generation', 'article_changed',
    'candidate_internal_error', 'lane_internal_error', 'checkpoint_sources_stale', 'provider_unavailable','evidence_source_changed'})
FINAL = frozenset({'duplicate_topic', 'duplicate_publication', 'stale_sources', 'invalid_official_announcement',
    'insufficient_independent_topic_sources', 'insufficient_official_documentation', 'documentation_topic_merged',
    'documentation_topic_not_actionable', 'unknown_blueprint', 'evergreen_missing_ai_application'})
VERSION = 1


def disposition(candidate):
    """Explicit panel semantics; old reasons remain available verbatim."""
    reason = candidate.reason
    state = candidate.state
    if state == 'published': kind = 'published'
    elif state=='technical_error': kind='technical_error'
    elif reason in FINAL or state == 'rejected' and reason not in CORRECTABLE | {'example_not_verified', 'publication_check_failed'}: kind = 'final_rejection'
    elif state == 'budget_pending' or reason in {'budget_exhausted', 'maintenance_budget_exhausted'}: kind = 'budget_pending'
    elif state in {'publication_error', 'needs_verification'} or reason == 'publication_check_failed': kind = 'publication_error'
    elif state == 'technical_error' or reason in TECHNICAL: kind = 'technical_error'
    elif state == 'correction_pending' or reason in CORRECTABLE | {'example_not_verified','numeric_review_pending'}: kind = 'correction_pending'
    else: kind = 'pending'
    recoverable = kind in {'budget_pending', 'correction_pending', 'publication_error'} and state != 'rejected'
    failure=next((f for f in [candidate.details.get('failure') or {},candidate.details.get('last_preflight_error') or {}]
                  if f.get('code')==reason),{})
    return {'kind': kind, 'recoverable': recoverable, 'reason': reason,
        'technical_code': (candidate.details.get('verification_error') if kind=='publication_error' else None) or reason,
        'details': failure.get('details', []), 'corrections_used': int(candidate.details.get('resume_report', {}).get('corrections_used', 0)),
        'correction_limit': 2, 'automatic_recoveries': candidate.details.get('automatic_recoveries', 0),
        'has_saved_draft': bool(candidate.details.get('resume_report', {}).get('proposal')),
        'next_attempt_at': candidate.next_attempt_at,
        'review_reasons': (candidate.details.get('resume_report', {}).get('review') or {}).get('reasons', [])[:8]}


def preserve(candidate, report, reason, details=None):
    """Retain paid material even after a correction/review rejection, not just timeouts."""
    data = dict(candidate.details, failure={'code': reason, 'details': details or []})
    if report.get('proposal') or report.get('stage_checkpoints'):
        saved = copy.deepcopy(report)
        saved['last_failure'] = {'code': reason, 'details': details or []}
        data['resume_report'] = saved
    candidate.details = data


def saved_reports(report):
    """Only traverse known report containers; never assign another candidate's draft."""
    found = []
    active = report.get('active_candidate_id') or report.get('policy', {}).get('candidate_id')
    if active and report.get('proposal'): found.append((active, report))
    for attempt in report.get('candidate_attempts', []):
        child = attempt.get('report') or {}
        if attempt.get('candidate_id') and child.get('proposal'):
            found.append((attempt['candidate_id'], child))
    for prior in report.get('prior_attempts', []):
        found.extend(saved_reports(prior.get('report') or {}))
    return found


async def recover_known_failures(db, now):
    """One migration of recoverable legacy rejections; no reset of money or attempts."""
    numeric_count=await recover_numeric_reviews(db,now)
    rows = (await db.scalars(select(EditorialCandidate).where(
        EditorialCandidate.state == 'rejected', EditorialCandidate.reason.in_(CORRECTABLE | {'publication_check_failed'})
    ).order_by(EditorialCandidate.id).limit(100))).all()
    rows = [r for r in rows if r.details.get('recovery_version') != VERSION]
    if not rows: return numeric_count
    histories = {}
    # Old and new workspaces have the same report contract.
    for model in (ResearchRun, EditorialLaneRun, EditorialExecution):
        for record in (await db.scalars(select(model).order_by(model.id).limit(500))).all():
            for cid, report in saved_reports(record.report): histories[cid] = report
    count = 0
    for row in rows:
        saved = copy.deepcopy(row.details.get('resume_report') or histories.get(row.id) or row.details.get('editorial_record') or {})
        if not saved.get('proposal') and row.reason != 'invalid_example': continue
        if any(e.get('state') in {'calling', 'reserving', 'uncertain'} for e in saved.get('stage_checkpoints', {}).values()): continue
        if row.reason == 'publication_check_failed':
            if not row.details.get('publication_snapshot') or not saved.get('approved_checkpoint'): continue
            state = 'publication_error'
        elif int(saved.get('corrections_used', 0)) < 2:
            state = 'correction_pending'
            saved['resume_correction'] = True
            saved['recovery_correction_limit'] = 2
        else: continue
        # A received provider response with an invalid example selection can be
        # decoded again using the constrained schema without a provider request.
        if row.reason == 'invalid_example' and not saved.get('proposal'):
            saved['recovery_decode'] = any(e.get('state') == 'response' for e in saved.get('stage_checkpoints', {}).values())
            saved['missing_retained_draft'] = not saved['recovery_decode']
        row.details = dict(row.details, resume_report=saved, recovery_version=VERSION,
            automatic_recoveries=int(row.details.get('automatic_recoveries', 0)) + 1,
            recovery_previous={'state':row.state,'reason':row.reason,'at':now.isoformat()})
        row.state, row.next_attempt_at = state, now
        db.add(AuditLog(actor='automation', action='candidate_recovery_prepared', entity_type='editorial_candidate',
            entity_id=row.id, details={'previous_reason':row.reason,'state':state,'no_provider_call':True}))
        count += 1
    await db.commit()
    return count+numeric_count


async def recover_numeric_reviews(db, now):
    """One review-only upgrade for the old numeric citation contract.

    Keep the two paid correction attempts and their expenditure. An old model
    approval with wrong numeric pointers is NOT an approval of publication.
    """
    from app.research.evidence import index
    from app.research.publication import article_snapshot
    from app.research.writing import Draft, GroundedReview, validate_draft
    from app.research.style import REVIEW_FLAGS
    rows=(await db.scalars(select(EditorialCandidate).where(
        EditorialCandidate.state=='rejected',EditorialCandidate.reason=='unsupported_number').limit(100))).all()
    count=0
    for row in rows:
        if row.details.get('numeric_review_upgrade')==2:continue
        saved=copy.deepcopy(row.details.get('resume_report') or {})
        if not saved.get('proposal') or not saved.get('review') or not row.article_id:continue
        if saved.get('policy',{}).get('numeric_citation_version')==2:continue
        if any(e.get('state') in {'calling','reserving','uncertain'} for e in saved.get('stage_checkpoints',{}).values()):continue
        try:
            verdict=GroundedReview.model_validate(saved['review'])
            if not all(getattr(verdict,k) is True for k in REVIEW_FLAGS):continue
            sources=saved['evidence_catalogue'];index(sources)
            proposal=Draft.model_validate(saved.get('evidence') or saved['proposal'])
            expected=validate_draft(proposal,sources,[],saved['policy'],provisional=True).model_dump(mode='json')
        except (ValueError,KeyError,StopRun):continue
        article=await db.get(Article,row.article_id)
        if not article or article.status!='draft' or any(getattr(article,k)!=v for k,v in expected.items()):continue
        saved.update(pending_review=True,resume_correction=False,policy=dict(saved['policy'],numeric_citation_version=2))
        saved.pop('approved_checkpoint',None)
        row.details=dict(row.details,resume_report=saved,numeric_review_upgrade=2,
                         numeric_review_snapshot=article_snapshot(article))
        row.state='deferred';row.reason='numeric_review_pending';row.next_attempt_at=now
        db.add(AuditLog(actor='automation',action='numeric_review_prepared',entity_type='editorial_candidate',entity_id=row.id,
                       details={'no_provider_call':True,'corrections_preserved':saved.get('corrections_used',0)}))
        count+=1
    await db.commit()
    return count


async def recover_publication(db, candidate, config, redis, token, now, verifier=None, receipt_path=None):
    """Revalidate a known approval and restore the SAME archived article, no model."""
    from app.research.worker import LOCK
    from app.models import ResearchControl
    from app.research.publication import article_snapshot, verify_candidate
    from app.research.executions import resume_material, digest
    from app.research.writing import Draft, Citation, GroundedReview, bind_reviewed_evidence, validate_draft
    from app.research.style import validate
    control = await db.scalar(select(ResearchControl).where(ResearchControl.id == 1).with_for_update())
    if not control or not control.enabled: raise StopRun('paused')
    if await redis.get(LOCK) != token: raise StopRun('lock_lost')
    candidate = await db.scalar(select(EditorialCandidate).where(EditorialCandidate.id == candidate.id)
        .with_for_update().execution_options(populate_existing=True))
    if candidate.state == 'published': return True
    if candidate.state != 'publication_error': raise StopRun('article_changed')
    article = await db.scalar(select(Article).where(Article.id == candidate.article_id).with_for_update())
    snapshot = candidate.details.get('publication_snapshot') or {}
    current = article_snapshot(article) if article else {}
    if not article or article.status != 'archived' or any(current.get(k) != v for k,v in snapshot.items() if k not in {'status','updated_at'}):
        raise StopRun('article_changed')
    withdrawn=candidate.details.get('withdrawal_snapshot')
    if withdrawn:
        if current!=withdrawn:raise StopRun('article_changed')
    else:
        audit=await db.scalar(select(AuditLog).where(AuditLog.entity_type=='article',AuditLog.entity_id==article.id,
            AuditLog.actor=='automation',AuditLog.action=='publication_withdrawn').order_by(AuditLog.id.desc()).limit(1))
        if not audit or audit.details.get('candidate_id')!=candidate.id or abs((aware(audit.created_at)-aware(article.updated_at)).total_seconds())>2:
            raise StopRun('article_changed')
    saved = candidate.details['resume_report']
    sources, policy, _, _ = await resume_material(db, candidate, now, receipt_path, allow_archived=True)
    draft = Draft.model_validate(saved['proposal']); validate(draft)
    bind_reviewed_evidence(draft, GroundedReview.model_validate(saved['review']), sources,policy)
    if saved.get('approved_checkpoint') != digest({'draft':draft.model_dump(mode='json'), 'catalogue':sources,
        'metadata':saved.get('reviewed_metadata_evidence', [])}): raise StopRun('article_changed')
    others = (await db.scalars(select(Article).where(Article.status == 'published', Article.id != article.id))).all()
    expected = validate_draft(draft, sources, others, policy,
        metadata_refs=[Citation.model_validate(r) for r in saved.get('reviewed_metadata_evidence', [])]).model_dump(mode='json')
    if any(getattr(article,k) != v for k,v in expected.items()): raise StopRun('article_changed')
    from app.research.quota import check_quota
    await check_quota(db, config, candidate, now)
    # Source revalidation can commit, so reacquire all final locks and recheck
    # the exact withdrawal snapshot before changing visibility.
    control=await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update().execution_options(populate_existing=True))
    if not control or not control.enabled:raise StopRun('paused')
    if await redis.get(LOCK)!=token:raise StopRun('lock_lost')
    candidate=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.id==candidate.id).with_for_update().execution_options(populate_existing=True))
    if candidate.state=='published':await db.commit();return True
    if candidate.state!='publication_error':raise StopRun('article_changed')
    article=await db.scalar(select(Article).where(Article.id==article.id).with_for_update().execution_options(populate_existing=True))
    if article_snapshot(article)!=current:raise StopRun('article_changed')
    await check_quota(db,config,candidate,now)
    article.status = 'published'  # Dates, URL, content, approvals and assets remain identical.
    article.updated_at=datetime.fromisoformat(snapshot['updated_at'])
    candidate.state = 'needs_verification'
    candidate.details = dict(candidate.details, verification_attempts=0,
        publication_recoveries=int(candidate.details.get('publication_recoveries',0)) + 1)
    db.add(AuditLog(actor='automation', action='publication_recovery', entity_type='article', entity_id=article.id,
        details={'candidate_id':candidate.id,'no_provider_call':True}))
    await db.commit()
    return await verify_candidate(db, candidate, verifier=verifier, now=now)
