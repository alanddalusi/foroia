"""Validación, revisión y una corrección acotada; jamás aprobar por agotamiento."""
import re
from sqlalchemy import select

from app.models import Article, AuditLog
from app.research.writing import (
    Draft, Review, StopRun, VOICE, CORRECT_INSTRUCTIONS, REVIEW_INSTRUCTIONS,
    REVIEW_MAX_OUTPUT_TOKENS, evidence_context, validate_draft,
)

FIXABLE = {'editorial_style_rejected', 'editorial_review_rejected', 'official_attribution_missing', 'official_scope_requires_corroboration', 'invalid_evidence', 'invalid_example', 'unsupported_number', 'invalid_article', 'unsafe_format',
           'insufficient_content', 'insufficient_independent_sources', 'copied_text', 'review_rejected'}
# Local checks that cost nothing to evaluate; only these may earn the bounded extra correction.
DETERMINISTIC = {'editorial_style_rejected', 'official_attribution_missing', 'official_scope_requires_corroboration',
                 'insufficient_content', 'unsupported_number', 'unsafe_format', 'copied_text'}


def resume_feedback(report):
    from app.research.style import review_feedback,REVIEW_FLAGS
    verdict=report.get('review') or {}
    feedback=review_feedback(verdict)
    if not verdict or all(verdict.get(k) is True for k in REVIEW_FLAGS):
        feedback=report.get('last_failure') or report.get('failure') or report.get('correction_feedback') or {'code':'editorial_style_rejected','details':[]}
    return dict(feedback,reasons=feedback.get('reasons') or ['Corrige el defecto señalado sin inventar hechos.'])


def complete_summary(text):
    """Remove a cut-off trailing sentence; never invent or complete a claim."""
    text=text.strip()
    if text.endswith(('.', '!', '?')):return text
    stops=list(re.finditer(r'[.!?](?=\s|$)',text))
    if stops and stops[-1].end()>=50:return text[:stops[-1].end()]
    return text


async def prepare(db, run, config, evidence, existing, budget, generator, resume=False,policy=None):
    policy=policy or {}
    from app.research.evidence import catalogue
    from app.research.sources import independent_organizations
    evidence = catalogue(evidence)
    if len(independent_organizations(evidence)) < policy.get('min_organizations',2):
        raise StopRun('insufficient_sources')
    # Persist exact input BEFORE any paid request. Never depend on a later refetch
    # to reconstruct which bytes the validator/generator saw.
    run.report = dict(run.report, evidence_catalogue=evidence, evidence_version=1)
    await db.commit()
    own_id = run.article_id
    existing = [a for a in existing if a.id != own_id]
    article, expected = None, None
    feedback = None
    used = int(run.report.get('corrections_used', 0))
    correction_limit=max(config.max_corrections, min(2,int(run.report.get('recovery_correction_limit',0))))
    versions = list(run.report.get('versions', []))[-2:]
    async def produce(*args):
        from app.research.writing import CHECKPOINT_STORE
        from app.research.checkpoints import store_for
        checkpoint_token=CHECKPOINT_STORE.set(store_for(db,run))
        try:
            result=await generator(*args)
            if isinstance(result,Draft) and policy.get('candidate_id'):
                if own_id and expected:
                    result.slug=expected['slug']
                    return result
                collision=await db.scalar(select(Article.id).where(Article.slug==result.slug))
                if collision and collision!=own_id:
                    base=result.slug[:150]+'-c'+str(policy['candidate_id'])
                    for attempt in range(1,10):
                        proposed=base if attempt==1 else base+'-'+str(attempt)
                        if not await db.scalar(select(Article.id).where(Article.slug==proposed)):
                            result.slug=proposed;break
                    else:raise StopRun('slug_conflict')
            return result
        except StopRun as exc:
            run.report = dict(run.report, generation_failure={'code': str(exc), 'details': exc.details})
            await db.commit()
            raise
        finally:CHECKPOINT_STORE.reset(checkpoint_token)
    if resume:
        if (resume != 'review' and used >= correction_limit) or (not run.article_id and resume!='correction') or not run.report.get('proposal'):
            raise StopRun('correction_limit_reached')
        draft = Draft.model_validate(run.report['proposal'])
        from app.research.writing import Citation
        # An unpublished rejected proposal may itself fail the check we are
        # about to correct. The saved article, when present, must still match
        # its immutable snapshot before editing it.
        if resume=='correction':
            row=await db.get(Article,own_id) if own_id else None
            if row:
                expected={k:getattr(row,k) for k in ['slug','title','summary','body','section','author_name','sources']}
            else:expected=None
        else:
            expected = validate_draft(draft, evidence, existing,policy,
                metadata_refs=[Citation.model_validate(r) for r in run.report.get('reviewed_metadata_evidence',[])],
                provisional=not run.report.get('citations_bound_by_review')).model_dump(mode='json')
        if resume == 'correction':
            feedback=resume_feedback(run.report)
        elif resume != 'review':
            feedback = {'code': 'review_rejected', 'reasons': (run.report.get('review') or {}).get('reasons', [])}
    else:
        recent=run.report.get('generation_recent_titles')
        if recent is None:
            recent=[a.title for a in existing[:80]]
            run.report=dict(run.report,generation_recent_titles=recent);await db.commit()
        draft = await produce(config, Draft, VOICE, {'sources': evidence, 'recent_titles': recent,'editorial_policy':policy}, budget)

    async def unchanged():
        if not own_id:
            return None
        row = await db.scalar(select(Article).where(Article.id == own_id).with_for_update().execution_options(populate_existing=True))
        if not row or row.status != 'draft' or any(getattr(row, k) != v for k, v in expected.items()):
            raise StopRun('article_changed')
        return row

    from app.research.executions import digest
    from app.research.style import validate as validate_style, STYLE_FLAGS, REVIEW_FLAGS
    if resume and all((run.report.get('review') or {}).get(k) is True for k in REVIEW_FLAGS) and run.report.get('approved_checkpoint')==digest({'draft':draft.model_dump(mode='json'),'catalogue':evidence,'metadata':run.report.get('reviewed_metadata_evidence',[])}):
        validate_style(draft)
        article=await unchanged()
        return article,validate_draft(draft,evidence,existing,policy,metadata_refs=[Citation.model_validate(r) for r in run.report.get('reviewed_metadata_evidence',[])])

    while True:
        if feedback:
            # One extra correction only when the paid correction introduced a NEW local,
            # deterministic failure (detected before paying a review). Never after a
            # review rejection, never for the same code twice, never more than once.
            previous_code=(run.report.get('correction_feedback') or {}).get('code')
            extra=(used>=correction_limit and used<2 and feedback['code'] in DETERMINISTIC
                   and feedback['code']!=previous_code and not run.report.get('deterministic_correction_used'))
            if feedback['code'] not in FIXABLE or (used >= correction_limit and not extra):
                raise StopRun(feedback['code'], feedback.get('details') or [])
            if extra:
                run.report=dict(run.report,deterministic_correction_used=True)
            await unchanged()
            used += 1
            from app.research.style import correction_plan
            feedback = dict(feedback, editing_plan=correction_plan(draft,feedback))
            run.report = dict(run.report, corrections_used=used, correction_feedback=feedback)
            db.add(AuditLog(actor='automation', action='research_correction', entity_type='research', entity_id=run.id, details={'attempt': used, 'reason': feedback['code']}))
            await db.commit()  # Reiniciar no concede correcciones ni gasto nuevos.
            try:
                fixed = await produce(config.model_copy(update={'max_output_tokens': REVIEW_MAX_OUTPUT_TOKENS}), Draft, CORRECT_INSTRUCTIONS,
                    {'draft': draft.model_dump(), 'errors': feedback, 'sources': evidence_context(draft, evidence),'editorial_policy':policy}, budget)
            except StopRun as exc:
                if str(exc)=='budget_exhausted':
                    used-=1
                    run.report=dict(run.report,corrections_used=used,resume_correction=True,recovery_correction_limit=correction_limit)
                    if extra:run.report=dict(run.report,deterministic_correction_used=False)
                    await db.commit()
                raise
            if own_id and fixed.slug != draft.slug:
                raise StopRun('article_changed')
            if feedback['code'] in {'editorial_style_rejected','editorial_review_rejected'}:
                from app.research.writing import normalize
                prose=lambda d:normalize(' '.join([d.title,d.summary,*[p.heading+' '+p.text for p in d.paragraphs]]))
                if prose(fixed)==prose(draft):
                    raise StopRun(feedback['code'],[{'code':'correction_no_progress','message':'La corrección no ha cambiado el texto rechazado; no se paga otra revisión idéntica.'}])
            draft = fixed
            run.report=dict(run.report,resume_correction=False)
        draft.summary=complete_summary(draft.summary)
        versions = [*versions, {'draft': draft.model_dump(mode='json')}][-3:]
        run.report = dict(run.report, proposal=draft.model_dump(mode='json'), model=config.model,
                          versions=versions, corrections_used=used, review=None)
        await db.commit()
        try:
            validate_style(draft)
            article_data = validate_draft(draft, evidence, existing,policy,provisional=True)
        except StopRun as exc:
            feedback = {'code': str(exc), 'reasons': ['Corrige el fallo determinista sin inventar evidencias.'],
                        'details': exc.details}
            versions = [*versions[:-1], dict(versions[-1], validation_error=str(exc), validation_details=exc.details)]
            run.report = dict(run.report, versions=versions)
            await db.commit()
            continue
        payload = article_data.model_dump(mode='json')
        article = await unchanged()
        if article:
            for key, value in payload.items():
                setattr(article, key, value)
        else:
            article = Article(**payload, status='draft')
            db.add(article)
            await db.flush()
            own_id = run.article_id = article.id
        expected = payload
        run.report = dict(run.report, evidence=draft.model_dump(mode='json'))
        run.report = dict(run.report, pending_review=True)
        db.add(AuditLog(actor='automation', action='research_draft', entity_type='article', entity_id=article.id, details={'run_id': run.id, 'correction': used}))
        await db.commit()
        review = await produce(config.model_copy(update={'max_output_tokens': REVIEW_MAX_OUTPUT_TOKENS}), Review, REVIEW_INSTRUCTIONS,
            {'draft': draft.model_dump(), 'sources': evidence_context(draft, evidence),'editorial_policy':policy}, budget)
        versions = [*versions[:-1], dict(versions[-1], review=review.model_dump())]
        run.report = dict(run.report, review=review.model_dump(), versions=versions, pending_review=False)
        run.report = dict(run.report, editorial_style={'version':1,'checks':{k:getattr(review,k) for k in STYLE_FLAGS}})
        await db.commit()
        if all(review.model_dump(exclude={'reasons'}).values()):
            from app.research.writing import bind_reviewed_evidence
            try:
                bound,metadata=bind_reviewed_evidence(draft,review,evidence,policy)
                final_data=validate_draft(bound,evidence,existing,policy,metadata_refs=metadata)
            except StopRun as exc:
                feedback={'code':str(exc),'details':exc.details,'reasons':['Corrige las afirmaciones o referencias que no superan la validación final.']}
                continue
            article=await unchanged()
            for key,value in final_data.model_dump(mode='json').items():setattr(article,key,value)
            run.report=dict(run.report,proposal=bound.model_dump(mode='json'),evidence=bound.model_dump(mode='json'),
                reviewed_metadata_evidence=[r.model_dump() for r in metadata],citations_bound_by_review=True)
            run.report=dict(run.report,pending_review=True,resume_correction=False,current_stage='ready_to_publish',approved_checkpoint=digest({'draft':bound.model_dump(mode='json'),'catalogue':evidence,'metadata':run.report['reviewed_metadata_evidence']}))
            await db.commit()
            return article, final_data
        if not review.safe_topic:
            raise StopRun('review_rejected')
        from app.research.style import review_feedback
        feedback = review_feedback(review.model_dump())
