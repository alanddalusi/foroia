"""Opt-in preflight using the documents fetched from official sites, never a model."""
import json,os
from pathlib import Path
import pytest
from sqlalchemy import select
from test_research import client,database
from test_editorial_engines import receipt,NOW
from app.models import EditorialCandidate
from app.research import queue,writing,evidence
from app.research.blueprints import BLUEPRINTS
from app.research.config import ResearchSettings

pytestmark=pytest.mark.skipif(os.environ.get('FOROIA_OFFICIAL_PREFLIGHT')!='1',reason='Explicit official-document snapshot required')


@pytest.mark.parametrize('blueprint',BLUEPRINTS,ids=lambda b:b.key)
def test_current_official_docs_fit_first_generation_without_spending(client,tmp_path,monkeypatch,blueprint):
    documents=json.loads(Path('.local/deploy/evergreen-official-documents.json').read_text(encoding='utf-8'))
    def forbidden(*args):pytest.fail('Preflight must not call any model')
    monkeypatch.setattr(writing,'call',forbidden)
    async def loader(db,url,now,budget):
        document=documents[url];assert 'error' not in document
        return document
    async def operation(db):
        await queue.seed_evergreen(db)
        row=next(c for c in (await db.scalars(select(EditorialCandidate))).all() if c.details['blueprint']==blueprint.key)
        docs,policy=await queue.prepare_candidate(db,row,NOW,{'remaining':4},doc_loader=loader,receipt_path=receipt(tmp_path))
        assert row.attempts==0 and row.state=='ready'
        assert policy['min_organizations']==(2 if blueprint.kind=='comparison' else 1)
        costs=[]
        async def preview(cost):costs.append(cost);raise writing.StopRun('preview')
        with pytest.raises(writing.StopRun,match='preview'):
            await writing.generate(ResearchSettings(),writing.Draft,writing.VOICE,{'sources':evidence.catalogue(docs),'editorial_policy':policy},preview)
        assert len(costs)==1 and 0<costs[0]<150000
    database(operation)
