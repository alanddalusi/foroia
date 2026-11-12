"""Final quota check under the same PostgreSQL control lock as publication."""
from datetime import datetime
from sqlalchemy import select, func, or_
from app.models import Article, EditorialCandidate, AuditLog
from app.research.config import MADRID
from app.research.writing import StopRun


async def check_quota(db, config, candidate, now, execution=None):
    if not config.two_lanes or candidate.target_article_id:
        return
    start = datetime.combine(now.astimezone(MADRID).date(), datetime.min.time(), tzinfo=MADRID)
    count = await db.scalar(select(func.count(EditorialCandidate.id)).join(Article,Article.id==EditorialCandidate.article_id).where(
        EditorialCandidate.engine==candidate.engine, EditorialCandidate.id!=candidate.id,
        EditorialCandidate.target_article_id.is_(None), Article.status=='published',
        or_(Article.published_at>=start,EditorialCandidate.published_at>=start)))
    limit = config.practical_publications if candidate.engine=='evergreen' else 1
    if count >= limit:
        permit=(execution.prepared or {}).get('backlog_authorization_id') if execution else None
        audit=await db.get(AuditLog,permit) if type(permit) is int else None
        scope=audit.details if audit and audit.action=='editorial_backlog_authorized' else {}
        ids=scope.get('candidate_ids',[])
        allowed=(execution and execution.candidate_id==candidate.id and candidate.engine=='evergreen'
            and scope.get('editorial_date')==str(now.astimezone(MADRID).date())
            and isinstance(ids,list) and 1<=len(ids)<=12 and len(set(ids))==len(ids)
            and candidate.id in ids and scope.get('maximum_publications')==len(ids))
        if not allowed:raise StopRun('daily_publication_limit')
