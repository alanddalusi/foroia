import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from test_research import client,database,Redis
from test_editorial_engines import NOW,docs,no_news,verifier,receipt,provider_factory
from test_evidence_first import approved_payload
from app.models import ResearchRun,ResearchControl,EditorialCandidate
from app.research import editorial,writing,queue
from app.research.config import ResearchSettings


@pytest.mark.parametrize('mode',['fixed','no_progress'])
def test_style_correction_receives_concrete_plan_and_cannot_approve_unchanged_text(client,tmp_path,monkeypatch,mode):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    base=provider_factory([]);calls=[];drafts=0
    def provider(config,payload):
        nonlocal drafts
        kind=payload['text']['format']['name'];calls.append(kind)
        if kind=='evergreendraft':
            drafts+=1
            data=json.loads(payload['input'])
            raw,usage=base(config,payload);value=json.loads(raw)
            if drafts==2:
                plan=data['errors']['editing_plan']
                assert plan['section_count']==(6 if mode=='fixed' else 4)
                assert plan['required_actions']
            if mode=='fixed' and drafts==1:
                text=' '.join(p['text'] for p in value['paragraphs']);words=text.split()
                for i in range(6):
                    part=' '.join(words[i*len(words)//6:(i+1)*len(words)//6])
                    if i<4:value['paragraphs'][i]['text']=part
                    else:value['paragraphs'].append(dict(value['paragraphs'][0],text=part))
                for i,p in enumerate(value['paragraphs']):p['heading']='Paso concreto '+str(i)
            return json.dumps(value),usage
        value=approved_payload(payload)
        if mode=='no_progress':value.update(approved=False,natural=False,reasons=['Reescribe el texto: las ideas no desarrollan la tarea.'])
        return json.dumps(value),{'input_tokens':100,'output_tokens':200}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate).order_by(EditorialCandidate.id))).all()
        for row in rows[1:]:row.state='deferred';row.next_attempt_at=NOW+timedelta(days=1)
        run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,
            doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        assert run.status==('published' if mode=='fixed' else 'skipped')
        assert drafts==2
        assert calls.count('groundedreview')==1
        if mode=='no_progress':assert run.report['candidate_attempts'][0]['reason']=='editorial_review_rejected'
    database(operation)


def test_semantic_structure_feedback_requests_merging_even_above_word_threshold():
    from test_research import draft
    from app.research.style import correction_plan
    value=draft();value.paragraphs=[value.paragraphs[i%4].model_copy(deep=True) for i in range(6)]
    for p in value.paragraphs:p.text+=' '+('Contexto documentado con límites claros. '*12)
    plan=correction_plan(value,{'code':'editorial_review_rejected','editorial_checks':{'well_structured':False}})
    assert plan['section_count']==6 and plan['prose_words']>350
    assert any('dos a cuatro' in action for action in plan['required_actions'])
