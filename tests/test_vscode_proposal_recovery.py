"""Saved production failure replayed without network or paid model calls."""
import copy,json
from contextlib import asynccontextmanager
from datetime import datetime,timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select,func
from test_research import client,database,Redis
from test_evidence_first import approved_payload
from test_editorial_engines import verifier
from app.models import ResearchControl,ResearchRun,EditorialCandidate,Article,GenerationUsage
from app.research import worker,writing
from app.research.config import ResearchSettings
from app.research.editorial_policy import validate_scope,policy_for,STRICT
from app.research.selection import normalize

CASE=json.loads(Path('tests/fixtures/official_vscode_20261029.json').read_text(encoding='utf-8'))
NOW=datetime.fromisoformat(CASE['source']['retrieved_at'])+timedelta(minutes=5)


def test_real_vs_code_sentence_is_not_a_comparison():
    source=CASE['source'];draft=writing.Draft.model_validate(CASE['draft'])
    assert 'VS Code' in ' '.join(p.text for p in draft.paragraphs)
    validate_scope(draft,[source],policy_for([source]))
    assert STRICT.search(normalize('OpenAI vs Google'))
    assert STRICT.search(normalize('Una comparación objetiva'))
    assert not STRICT.search(normalize('La integración con VS Code'))
    assert not STRICT.search(normalize('Microsoft comparte herramientas para responder a la demanda empresarial'))


@pytest.mark.parametrize('mode',['valid','rejected','uncertain','tampered','budget'])
def test_saved_proposal_reuses_draft_and_only_reviews(client,monkeypatch,mode):
    monkeypatch.setattr(worker,'utcnow',lambda:NOW)
    monkeypatch.setattr(worker,'settings',lambda:ResearchSettings(api_key='offline',daily_usd=Decimal('.20'),monthly_usd=Decimal('10')))
    r=Redis();monkeypatch.setattr(worker,'get_redis',lambda:r)
    calls=[]
    def provider(config,payload):
        assert payload['text']['format']['name']=='groundedreview'
        calls.append('Review');value=approved_payload(payload)
        if mode=='rejected':value.update(approved=False,supported=False,reasons=['Simulated rejection: unsupported claim'])
        return json.dumps(value),{'input_tokens':100,'output_tokens':200}
    monkeypatch.setattr(writing,'call',provider)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        source=copy.deepcopy(CASE['source']);draft=copy.deepcopy(CASE['draft']);policy=policy_for([source])
        for paragraph in draft['paragraphs']:
            for key in ('heading','text'):
                if paragraph[key].startswith('Según Microsoft, '):paragraph[key]=paragraph[key][len('Según Microsoft, '):]
        draft['paragraphs']=[{'heading':heading,'text':' '.join(p['text'] for p in draft['paragraphs'][i:i+2]),
                             'evidence':[r for p in draft['paragraphs'][i:i+2] for r in p['evidence']]}
                            for i,heading in zip(range(0,len(draft['paragraphs']),2),['Qué se anuncia','Integración y alcance','Ejecución y herramientas'])]
        candidate=EditorialCandidate(fingerprint='isolated-vscode-event',engine='news',kind='news',topic=source['title'],section='actualidad',intent='Understand the announcement',keyword='Microsoft Copilot harness',state='rejected',reason='official_scope_requires_corroboration',attempts=1,details={'sources':[source]})
        db.add(candidate);await db.flush();policy.update(kind='news',candidate_id=candidate.id)
        if mode=='tampered':source['text']+='tampered'
        saved={'proposal':draft,'evidence_catalogue':[source],'policy':policy,'corrections_used':1,
               'stage_checkpoints':{'example':{'state':'calling' if mode=='uncertain' else 'complete'}},'review':None}
        run=ResearchRun(editorial_date=NOW.date(),status='skipped',reason='news_only_no_verified_publication',reserved_microusd=199999 if mode=='budget' else 109411,
                        report={'manual_news_retry':{'result':{'new_article_id':None}},'candidate_attempts':[{'candidate_id':candidate.id,'report':saved}]})
        db.add(run);await db.commit()
        @asynccontextmanager
        async def session():yield db
        monkeypatch.setattr(worker,'get_sessionmaker',lambda:session)
        if mode in {'uncertain','tampered'}:
            with pytest.raises((writing.StopRun,ValueError)):await worker.resume_proposal(run.id,verifier=verifier)
            assert not calls
        else:
            await worker.resume_proposal(run.id,verifier=verifier)
            assert run.reserved_microusd<=200000
            assert run.report['corrections_used']==1
            assert run.report['candidate_attempts'][0]['report']['proposal']==draft
            assert await db.scalar(select(func.count(Article.id)).where(Article.status=='published'))==(1 if mode=='valid' else 0)
            assert calls==([] if mode=='budget' else ['Review'])
            with pytest.raises(writing.StopRun):await worker.resume_proposal(run.id,verifier=verifier)
            uses=(await db.scalars(select(GenerationUsage))).all()
            assert all(u.stage=='Review' for u in uses)
    database(operation)
