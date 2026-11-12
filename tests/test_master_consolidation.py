"""Opportunities, existing health timer, truthful analytics and protected maintenance."""
import json
from datetime import UTC,datetime,timedelta
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest
from sqlalchemy import select,func
from test_research import client,database,Redis
from test_accounts_api import account_client,seed_user,session
from test_articles_api import article as payload,AUTH
from test_editorial_engines import NOW,receipt,docs,no_news,verifier,provider_factory
from app.models import Article,EditorialCandidate,ResearchRun,ResearchControl,AuditLog
from app.research import monitor,queue,editorial,writing,worker
from app.research.config import ResearchSettings
from app.research.opportunities import opportunity


def test_opportunity_is_explicit_hypothesis_not_fabricated_demand():
    row=SimpleNamespace(topic='Validar JSON con Python',keyword='validar json python',intent='Validar entradas',kind='tutorial',
        details={'sources':['https://docs.python.org/3.12/library/json.html'],'demand_source':'editorial_hypothesis'})
    article=SimpleNamespace(id=1,slug='validar-json-python',title='Validar JSON con Python')
    data=opportunity(row,[article],NOW)
    assert data['cannibalization_risk']=='high' and data['related_content'][0]['article_id']==1
    assert data['search_volume'] is data['seo_difficulty'] is data['trend'] is None
    assert data['evidence_status']=='planned' and data['regional_versions'] is False
    assert data['related_questions']==['¿Cómo validar json python?']


class HealthRedis:
    def __init__(self,alive=True):self.data={'foroia:research:heartbeat':b'alive'} if alive else {}
    async def get(self,key):return self.data.get(key)
    async def set(self,key,value,ex=None):self.data[key]=value;return True


@pytest.mark.parametrize('published',[True,False])
def test_manual_budget_bucket_uses_actual_verified_publication(client,monkeypatch,published):
    monkeypatch.setattr(monitor,'get_settings',lambda:SimpleNamespace(site_url='https://foroia.test'))
    monkeypatch.setattr(monitor,'settings',lambda:ResearchSettings())
    stamp=datetime(2026,10,26,22,55,tzinfo=UTC)
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        article=Article(**payload(),status='published' if published else 'draft',published_at=stamp)
        db.add(article);await db.flush()
        db.add(ResearchRun(editorial_date=stamp.date(),status='skipped',reason='manual_budget_bucket'))
        db.add(EditorialCandidate(fingerprint='manual-health',engine='evergreen',kind='guide',topic='Guide',section='tutoriales',intent='Task',keyword='keyword',state='published' if published else 'deferred',published_at=stamp,article_id=article.id))
        await db.commit()
        result=await monitor.inspect(db,HealthRedis(),stamp,website(article if published else None))
        assert ('no_publication_today' in result['alerts']) is not published
    database(operation)


def website(article=None,broken=False):
    site='https://foroia.test'
    def get(url):
        path=urlsplit(url).path
        if broken and path=='/sitemap.xml':raise OSError('temporary failure')
        if path=='/':return '<link rel="canonical" href="'+site+'/"><a href="/articulos/'+(article.slug if article else 'none')+'">Article</a>'
        if path=='/robots.txt':return 'User-agent: *\nAllow: /\nSitemap: '+site+'/sitemap.xml\n'
        if path=='/sitemap.xml':return '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>'+site+'/sitemap-pages.xml</loc></sitemap></sitemapindex>'
        if path=='/sitemap-pages.xml':return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+site+'/</loc></url>'+('<url><loc>'+site+'/articulos/'+article.slug+'</loc></url>' if article else '')+'</urlset>'
        if article and path=='/articulos/'+article.slug:return '<link rel="canonical" href="'+url+'"><meta name="description" content="'+article.summary+'">'
        raise AssertionError(path)
    return get


@pytest.mark.parametrize('mode',['healthy','stopped','late','budget','broken'])
def test_monitor_alerts_are_bounded_deduplicated_and_private(client,monkeypatch,mode):
    monkeypatch.setattr(monitor,'get_settings',lambda:SimpleNamespace(site_url='https://foroia.test'))
    monkeypatch.setattr(monitor,'settings',lambda:ResearchSettings())
    stamp=datetime(2026,10,25,21,55,tzinfo=UTC) if mode=='late' else datetime(2026,10,25,12,tzinfo=UTC)
    redis=HealthRedis(alive=mode!='stopped')
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True))
        article=Article(**payload(),status='published',published_at=stamp);db.add(article)
        if mode=='budget':db.add(ResearchRun(editorial_date=stamp.date(),reserved_microusd=5_000_000))
        await db.commit()
        one=await monitor.inspect(db,redis,stamp,website(article,mode=='broken'))
        count=await db.scalar(select(func.count()).select_from(AuditLog))
        two=await monitor.inspect(db,redis,stamp,website(article,mode=='broken'))
        assert count==await db.scalar(select(func.count()).select_from(AuditLog))
        expected={'healthy':None,'stopped':'worker_heartbeat_missing','late':'scheduled_run_missing','budget':'monthly_budget_exhausted','broken':'public_seo_check_failed'}[mode]
        assert (one['alerts']==[]) if expected is None else expected in one['alerts']
        if mode=='healthy':
            assert one['seo']['sitemap_urls']==2 and one['seo']['sampled_articles']==1
            assert one['seo']['orphan_articles']==[] and one['seo']['all_articles_checked']
        assert one['notification_channel']=='systemd_journal_and_private_panel'
    database(operation)
    assert client.get('/editorial/research').status_code==401


@pytest.mark.parametrize('url',['https://evil.test/a','http://foroia.test/a','https://foroia.test/a?x=1','https://foroia.test/a#b'])
def test_monitor_rejects_noncanonical_or_foreign_sitemap_destinations(url):
    xml='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+url+'</loc></url></urlset>'
    with pytest.raises(ValueError):monitor.locations(xml,'https://foroia.test')


def test_metric_gaps_are_null_not_invented_users(client):
    data=client.get('/editorial/analytics',headers=AUTH).json()['measurement']
    assert data['ga4']['unique_users'] is None and data['ga4']['countries'] is None
    assert data['search_console']['clicks'] is None


def test_invalid_search_console_counts_rejected(account_client,monkeypatch):
    from app.research import routes
    monkeypatch.setattr(routes,'get_redis',lambda:Redis())
    seed_user(role='editor');headers=session(account_client)
    body={'source':'search_console_export','signals':[{'query':'validar json python','impressions':0,'clicks':10,'position':3}]}
    assert account_client.post('/editorial/research/signals',headers=headers,json=body).status_code==422


def test_weekly_update_cap_keeps_new_content_moving(client,tmp_path,monkeypatch):
    monkeypatch.setattr(editorial,'utcnow',lambda:NOW)
    calls=[];monkeypatch.setattr(writing,'call',provider_factory(calls))
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));article=Article(**payload(),status='published',published_at=NOW);db.add(article);await db.flush()
        db.add(EditorialCandidate(fingerprint='a'*64,engine='evergreen',kind='update',topic='Older update',section='tutoriales',intent='Update',keyword='Update',
            state='published',target_article_id=article.id,published_at=NOW))
        update=EditorialCandidate(fingerprint='b'*64,engine='evergreen',kind='update',topic='Another update',section='tutoriales',intent='Update',keyword='Update',
            state='queued',priority=100,target_article_id=article.id)
        db.add(update);run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        redis=Redis();redis.value=b'owner'
        await editorial.execute(db,run,ResearchSettings(),redis,b'owner',news_collector=no_news,doc_loader=docs,verifier=verifier,receipt_path=receipt(tmp_path))
        assert update.reason=='maintenance_weekly_cap' and update.attempts==0
        assert run.status=='published' and run.article_id!=article.id and len(calls)==2
    database(operation)


def test_update_budget_does_not_spend_new_content_allowance(client):
    async def operation(db):
        db.add(ResearchControl(id=1,enabled=True));run=ResearchRun(editorial_date=NOW.date());db.add(run);await db.commit()
        document=await docs(db,'https://docs.python.org/3.12/library/json.html',NOW,{'remaining':1})
        async def collector(now,urls):return [document],{'candidate_count':1}
        async def generator(config,schema,instructions,data,reserve):
            await reserve(60001)
            pytest.fail('No generation permitted outside maintenance allowance')
        redis=Redis();redis.value=b'owner'
        with pytest.raises(writing.StopRun,match='maintenance_budget_exhausted'):
            await worker.pipeline(db,run,ResearchSettings(),redis,b'owner',collector,generator,
                policy={'kind':'guide','operation':'update','min_organizations':1,'max_operation_microusd':60000})
        assert run.reserved_microusd==0
    database(operation)


def test_off_production_receipt_is_bound_to_code_dependencies_and_runtime(tmp_path):
    from app.research.examples import verified_example,dependency_hash,runtime_versions
    path=receipt(tmp_path,NOW-timedelta(days=30))
    data=json.loads(__import__('pathlib').Path(path).read_text())
    data.update(mode='immutable_build_artifact',execution_location='off_production',dependency_sha256=dependency_hash(),runtime=runtime_versions())
    target=__import__('pathlib').Path(path);target.write_text(json.dumps(data))
    assert verified_example('json_validation',path,NOW)
    data['dependency_sha256']='bad';target.write_text(json.dumps(data));assert not verified_example('json_validation',path,NOW)
    data['dependency_sha256']=dependency_hash();data['runtime']['python']='0.0.0';target.write_text(json.dumps(data));assert not verified_example('json_validation',path,NOW)
    data['runtime']=runtime_versions();data['execution_location']='production';target.write_text(json.dumps(data));assert not verified_example('json_validation',path,NOW)
