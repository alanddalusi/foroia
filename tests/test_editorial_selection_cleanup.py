"""Small regressions for the real queue/metrics bugs; no network or model calls."""
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import select,func
from test_research import client,database,Redis
from test_articles_api import AUTH,article
from test_editorial_engines import NOW
from app.research.blueprints import BLUEPRINTS
from app.models import Article,EditorialCandidate,EditorialExecution,AuditLog,SourceCache,ResearchControl
from app.research import queue,routes
from app.research.blueprints import BY_KEY
from app.research.opportunities import opportunity


def test_document_headings_do_not_create_topics_and_legacy_rows_are_grouped(client):
    async def operation(db):
        await queue.seed_evergreen(db)
        parent=await db.scalar(select(EditorialCandidate).where(EditorialCandidate.details['blueprint'].as_string()=='gemini-prompts'))
        url=BY_KEY['gemini-prompts'].docs[0]
        db.add(SourceCache(url=url,content_sha256='x'*64,fetched_at=NOW,expires_at=NOW+timedelta(days=1),document={'sections':[{'key':'input','title':'Input','text':'Original documentation. '*50}]}))
        await db.commit()
        assert await queue.discover_document_opportunities(db,NOW)==0
        assert await db.scalar(select(func.count(EditorialCandidate.id)))==len(BLUEPRINTS)
        originals=[]
        for i,heading in enumerate(['Input','Constraints','Unknown']):
            focus=url if i<2 else 'https://unknown.example/docs'
            row=EditorialCandidate(fingerprint='legacy-section-'+str(i),engine='evergreen',kind='guide',topic='Uso de '+heading+' con google',section='herramientas',intent='Old generated index',keyword=heading,state='queued',details={'focus':{'url':focus,'key':heading},'sources':[focus],'demand_source':'official_document_section_hypothesis'})
            db.add(row);originals.append(row)
        await db.commit()
        assert await queue.discover_document_opportunities(db,NOW)==3
        assert await queue.discover_document_opportunities(db,NOW)==0
        assert await db.scalar(select(func.count(EditorialCandidate.id)))==len(BLUEPRINTS)+3
        for row in originals[:2]:
            assert row.state=='rejected' and row.reason=='documentation_topic_merged'
            assert row.details['queue_audit']['merged_into_candidate_id']==parent.id
            assert row.details['sources']==[url] and row.attempts==0
        assert originals[-1].reason=='documentation_topic_not_actionable'
        assert await db.scalar(select(func.count(Article.id)))==0
    database(operation)


def test_existing_blueprint_titles_are_updated_only_before_work_starts(client):
    async def operation(db):
        await queue.seed_evergreen(db)
        rows=(await db.scalars(select(EditorialCandidate))).all()
        first=next(r for r in rows if r.details['blueprint']=='save-summaries')
        worked=next(r for r in rows if r.details['blueprint']=='fastapi-prompts')
        first.topic='Old generic title';worked.topic='Existing attempted title';worked.attempts=1
        original_id=first.id;await db.commit()
        await queue.seed_evergreen(db)
        assert first.id==original_id and first.topic==BY_KEY['save-summaries'].topic
        assert first.details['queue_audit']['previous']['topic']=='Old generic title'
        assert worked.topic=='Existing attempted title' and worked.attempts==1
        assert await db.scalar(select(func.count(EditorialCandidate.id)))==len(BLUEPRINTS)
    database(operation)


def test_opportunity_distinguishes_editorial_fit_from_unmeasured_demand():
    b=BY_KEY['fastapi-prompts']
    row=SimpleNamespace(topic=b.topic,keyword=b.keyword,intent=b.intent,kind=b.kind,engine='evergreen',details={'blueprint':b.key,'sources':list(b.docs)})
    value=opportunity(row,[],NOW)
    assert value['assessment']['practical_application']
    assert value['assessment']['example_id']=='fastapi_body'
    assert value['assessment']['traffic_potential']['status']=='not_measured'
    assert value['search_volume'] is value['seo_difficulty'] is None
    row.keyword=''
    assert opportunity(row,[],NOW)['related_questions']==[]


def test_counts_are_distinct_articles_and_historical_events_not_article_ids(client,monkeypatch):
    monkeypatch.setattr(routes,'get_redis',lambda:Redis())
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        for identifier,status in [(10,'published'),(11,'archived'),(12,'published')]:
            db.add(Article(id=identifier,**article(slug='count-'+str(identifier)),status=status,published_at=NOW))
        await db.flush()
        for i,identifier in enumerate([10,10,11]):
            db.add(EditorialCandidate(fingerprint='verified-event-'+str(i),engine='news',kind='news',topic='Verified event',section='actualidad',intent='Understand event',keyword='event',state='published',article_id=identifier,details={'verification':dict(api=True,html=True,seo=True,sitemap=True)}))
        for _ in range(2):db.add(AuditLog(actor='automation',action='publication_verified',entity_type='article',entity_id=10))
        db.add(EditorialExecution(request_key='completed-job',mode='new',state='completed'))
        db.add(EditorialExecution(request_key='failed-job',mode='new',state='failed'))
        await db.commit()
    database(operation)
    r=client.get('/editorial/research',headers=AUTH);assert r.status_code==200,r.text
    counts=r.json()['content_counts']
    assert counts['published_articles']==2 and counts['verified_published_articles']==1
    assert counts['verified_publication_events']==2 and counts['completed_manual_executions']==1
