"""Commit the request boundary and response before any later validation/publication."""
from app.models import utcnow
from app.research.writing import StopRun


async def settle_completed(db,run,config):
    """Release only proven unused reserves; uncertain calls remain fully charged.

    Durable audit deduplication survives restoration of an older report snapshot.
    The same control-row lock serializes this with every budget reservation.
    Manual execution quotes keep their existing conservative accounting.
    """
    if hasattr(run,'execution'):return
    budget_run=getattr(run,'budget_run',run)
    owner=getattr(run,'lane',run)
    from sqlalchemy import select
    from app.models import ResearchControl,GenerationUsage,AuditLog
    await db.scalar(select(ResearchControl).where(ResearchControl.id==1).with_for_update())
    await db.refresh(budget_run,attribute_names=['reserved_microusd'])
    await db.refresh(owner,attribute_names=['report'])
    for key,entry in run.report.get('stage_checkpoints',{}).items():
        if entry.get('state')!='response' or entry.get('editorial_date')!=str(run.editorial_date):continue
        ledger_key=entry.get('ledger_key')
        usage=entry.get('usage',{})
        incoming,outgoing=usage.get('input_tokens'),usage.get('output_tokens')
        maximum=entry.get('maximum_microusd')
        if any(type(v) is not int or v<0 for v in [incoming,outgoing,maximum]):continue
        ledger=await db.scalar(select(GenerationUsage).where(GenerationUsage.request_key==ledger_key))
        if not ledger or ledger.run_id!=run.id or ledger.model!=config.model or ledger.stage!=entry.get('stage'):continue
        if ledger.input_tokens!=incoming or ledger.output_tokens!=outgoing or not 0<=ledger.estimated_microusd<=maximum:continue
        # This ledger is written only after receiving usage. Never infer zero.
        if await db.scalar(select(AuditLog.id).where(AuditLog.action=='research_reservation_settled',
                AuditLog.entity_type=='research',AuditLog.entity_id==run.id,
                AuditLog.details['request_key'].as_string()==ledger_key).limit(1)):continue
        released=maximum-ledger.estimated_microusd
        if released>budget_run.reserved_microusd:raise StopRun('reservation_accounting_mismatch')
        budget_run.reserved_microusd-=released
        db.add(AuditLog(actor='automation',action='research_reservation_settled',entity_type='research',entity_id=run.id,
            details={'request_key':ledger_key,'maximum_microusd':maximum,'reported_microusd':ledger.estimated_microusd,
                'released_microusd':released,'billing_verified':False}))
    await db.commit()


def retryable_incomplete(entry,day):
    # A received incomplete response is a known result, unlike a transport timeout.
    # At most one paid retry, on a later editorial day, under ordinary budgets.
    return (entry.get('state')=='failed' and entry.get('reason')=='incomplete_generation'
        and int(entry.get('attempt_count',1))<2 and bool(entry.get('editorial_date'))
        and str(day)>entry['editorial_date'])


def store_for(db,run):
    async def store(event,key,data):
        entries=dict(run.report.get('stage_checkpoints',{}));entry=dict(entries.get(key,{}))
        if event=='lookup':
            expected=getattr(run,'expected_request_hash',None)
            if expected and not run.report.get('manual_request_started') and key!=expected:raise StopRun('quote_changed')
            if entry.get('state')=='response':return entry
            if entry.get('state') in {'reserving','calling','uncertain'}:raise StopRun('uncertain_provider_result',[{'request_hash':key}])
            if entry.get('state')=='failed':
                if retryable_incomplete(entry,run.editorial_date):return None
                raise StopRun(entry['reason'],entry.get('details'))
            return None
        if event=='unfunded':
            previous=entry.get('intent_previous',{})
            if previous:entries[key]=previous
            else:entries.pop(key,None)
            run.report=dict(run.report,stage_checkpoints=entries);await db.commit();return
        if event=='intent':
            previous=dict(entry)
            entry.update(data,state='reserving',at=utcnow().isoformat(),editorial_date=str(run.editorial_date),intent_previous=previous)
            if hasattr(run,'execution'):entry['execution_id']=run.execution.id
        elif event=='calling':
            entry.pop('intent_previous',None)
            entry.update(data,state='calling',at=utcnow().isoformat(),attempt_count=int(entry.get('attempt_count',0))+1)
        elif event=='response':
            if len(data['raw'].encode())>100000:raise StopRun('provider_response_too_large')
            entry.update(data,state='response',at=utcnow().isoformat())
        elif event=='failed':
            known=any(d.get('http_status') for d in data.get('details',[]) if isinstance(d,dict)) or data['reason'] in {'incomplete_generation','provider_refusal'}
            entry.update(data,state='failed' if known else 'uncertain',at=utcnow().isoformat())
        entries[key]=entry
        if len(entries)>8:entries=dict(sorted(entries.items(),key=lambda p:p[1].get('at',''))[-8:])
        run.report=dict(run.report,stage_checkpoints=entries,current_stage=entry.get('stage','validation'),manual_request_started=True)
        await db.commit()
    return store
