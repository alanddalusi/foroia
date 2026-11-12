"""One-shot, read-only observation. Never imports or calls the generation pipeline."""
import argparse
from datetime import UTC, date, datetime, time as daytime
from decimal import Decimal
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

MADRID = ZoneInfo('Europe/Madrid')
BASE = 'https://foroiaaldia.com'
SNAPSHOT = '''import asyncio,json,sys
from datetime import date
from sqlalchemy import select,func,text
from app.core.db import get_sessionmaker
from app.core.limits import get_redis
from app.models import Article,ResearchRun,ResearchControl
from app.research.config import settings
async def main():
 day=date.fromisoformat(sys.argv[1]);month=day.replace(day=1)
 end=date(day.year+1,1,1) if day.month==12 else date(day.year,day.month+1,1)
 async with get_sessionmaker()() as db:
  await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
  row=await db.scalar(select(ResearchRun).where(ResearchRun.editorial_date==day))
  total=await db.scalar(select(func.coalesce(func.sum(ResearchRun.reserved_microusd),0)).where(ResearchRun.editorial_date>=month,ResearchRun.editorial_date<end))
  config=settings();control=await db.get(ResearchControl,1)
  result={'date':str(day),'monthly_reserved_microusd':total,'configuration':{'at':config.at.isoformat(),'timezone':'Europe/Madrid','model':config.model,'monthly_usd':str(config.monthly_usd),'daily_usd':str(config.daily_usd),'auto_publish':config.auto_publish,'enabled':bool(control and control.enabled)},'run':None,'article':None}
  if row:
   result['run']={k:getattr(row,k) for k in ['id','status','reason','reserved_microusd','article_id','created_at','finished_at','report']}
   if row.article_id:
    article=await db.get(Article,row.article_id)
    if article:result['article']={k:getattr(article,k) for k in ['id','slug','status','title','summary','body','section','author_name','sources','published_at','updated_at','reviewed_at','reviewed_by']}
  try:result['worker_alive']=bool(await get_redis().get('foroia:research:heartbeat'))
  except Exception:result['worker_alive']=False
  print(json.dumps(result,default=str,ensure_ascii=False))
asyncio.run(main())
'''


def capture(day):
    output = subprocess.check_output(['docker', 'exec', 'foroia-production-api-1', 'python', '-c', SNAPSHOT, day], timeout=25)
    result = json.loads(output)
    raw = subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', 'foroia-production-research-worker-1'], timeout=10)
    state = json.loads(raw)
    result['container'] = {k: state.get(k) for k in ['Running', 'StartedAt', 'ExitCode']}
    return result


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.meta, self.canonical, self.links, self.schemas = {}, [], [], []
        self.h1, self.title, self.tag, self.script = '', '', '', None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta': self.meta[a.get('name') or a.get('property')] = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href'))
        if tag == 'a': self.links.append(a.get('href'))
        if tag in ['title', 'h1']: self.tag = tag
        if tag == 'script' and a.get('type') == 'application/ld+json': self.script = ''

    def handle_data(self, data):
        if self.script is not None: self.script += data
        elif self.tag == 'title': self.title += data
        elif self.tag == 'h1': self.h1 += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.schemas.append(json.loads(self.script)); self.script = None
        if tag == self.tag: self.tag = ''


def request(url, data=None):
    req = Request(url, data=data, headers={'User-Agent': 'ForoIA read-only scheduled audit', 'Accept': 'text/html,application/json,application/xml'})
    with urlopen(req, timeout=20) as response:
        if response.status != 200: raise ValueError('unexpected_http_status')
        body = response.read(2_000_001)
        if len(body) > 2_000_000: raise ValueError('response_too_large')
        return body.decode('utf-8')


def public_checks(article):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', article['slug']): raise ValueError('invalid_slug')
    url = BASE + '/articulos/' + article['slug']
    page = Page(request(url))
    api = json.loads(request(BASE + '/api/articles/' + article['slug']))
    schemas = [item for group in page.schemas for item in (group if isinstance(group, list) else [group])]
    sitemap_urls = []
    for loc in ElementTree.fromstring(request(BASE + '/sitemap.xml')).findall('.//{*}loc')[:20]:
        if re.fullmatch(re.escape(BASE) + r'/sitemaps/articles/[1-9][0-9]*', loc.text or ''):
            sitemap_urls += [n.text for n in ElementTree.fromstring(request(loc.text)).findall('.//{*}loc')]
    result = {'url': url, 'h1_matches': page.h1.strip() == article['title'], 'title_matches': article['title'] in page.title,
        'description_matches': page.meta.get('description') == article['summary'], 'canonical_matches': page.canonical == [url],
        'open_graph_matches': page.meta.get('og:url') == url and page.meta.get('og:title') == article['title'],
        'indexable': 'noindex' not in (page.meta.get('robots') or ''), 'in_sitemap': url in sitemap_urls,
        'body_and_sources_match': all(api[k] == article[k] for k in ['body', 'sources', 'summary', 'title', 'section']),
        'source_links_present': all(s['url'] in page.links for s in article['sources']),
        'schema_types_present': any('BlogPosting' in n.get('@type', []) for n in schemas) and any(n.get('@type') == 'BreadcrumbList' for n in schemas)}
    try:
        raw = request('https://validator.schema.org/validate', urlencode({'url': url}).encode())
        validated = json.loads(raw.split('\n', 1)[1] if raw.startswith(")]}'") else raw)
        result['schema_validator'] = {k: validated.get(k) for k in ['numObjects', 'totalNumErrors', 'totalNumWarnings']}
    except Exception as exc:
        result['schema_validator'] = {'not_completed': type(exc).__name__}
    return result


def summarize(snapshot, timeline, timed_out=False, checks=None):
    run = snapshot.get('run') or {}
    report = run.get('report') or {}
    config = snapshot.get('configuration') or {}
    versions = []
    for i, version in enumerate(report.get('versions', []), 1):
        versions.append({'version': i, 'title': version.get('draft', {}).get('title'),
            'deterministic_validation': version.get('validation_error') or ('passed' if version.get('review') or ('evidence' in report and version.get('draft') is not None and version['draft'] == report['evidence']) else 'not_recorded'),
            'review': version.get('review') or 'not_evaluated_or_not_recorded'})
    return {'date': snapshot.get('date'), 'status': run.get('status', 'no_execution_recorded'), 'reason': run.get('reason'),
        'worker_alive': snapshot.get('worker_alive'), 'created_at': run.get('created_at'), 'finished_at': run.get('finished_at'),
        'scheduled_feed_count': report.get('feed_count'), 'candidate_document_count': report.get('candidate_count'),
        'recovered_documents': len(report['sources']) if 'sources' in report else None,
        'fetch_errors': report.get('fetch_errors', []), 'fetch_failure_count': report.get('fetch_failures'),
        'confirmed_organizations': report.get('source_organizations'), 'article_versions': versions,
        'selection_limit': 'One article daily with at most one correction; candidates are documents, not separately drafted articles.',
        'daily_reserved_usd': str(Decimal(run.get('reserved_microusd', 0)) / 1_000_000),
        'monthly_reserved_usd': str(Decimal(snapshot.get('monthly_reserved_microusd', 0)) / 1_000_000),
        'daily_within_limit': run.get('reserved_microusd', 0) <= Decimal(config['daily_usd']) * 1_000_000 if run and 'daily_usd' in config else None,
        'monthly_within_limit': snapshot['monthly_reserved_microusd'] <= Decimal(config['monthly_usd']) * 1_000_000 if 'monthly_reserved_microusd' in snapshot and 'monthly_usd' in config else None,
        'budget_scope': 'Conservative reservations, not provider billing independently verified.',
        'public_checks': checks, 'observation_deadline_reached': timed_out, 'timeline': timeline}


def save(directory, snapshot, timeline, timed_out=False, checks=None):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = summarize(snapshot, timeline, timed_out, checks)
    for name, value in [('report.json', result), ('snapshot.json', snapshot)]:
        target = directory / name
        temp = directory / (name + '.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, target)
    lines = ['# Investigación nocturna: ' + str(result['date']), '',
        '- Estado: ' + str(result['status']), '- Motivo: ' + str(result['reason']),
        '- Candidatos documentales: ' + str(result['candidate_document_count']),
        '- Documentos recuperados: ' + str(result['recovered_documents']),
        '- Consultas fallidas: ' + str(result['fetch_failure_count']),
        '- Reserva del día: ' + result['daily_reserved_usd'] + ' USD.',
        '- Reserva del mes: ' + result['monthly_reserved_usd'] + ' USD.',
        '- Límites respetados: día=' + str(result['daily_within_limit']) + ', mes=' + str(result['monthly_within_limit']),
        '', 'El detalle de descargas, versiones, controles y comprobaciones públicas está en report.json.',
        'No se han forzado generaciones ni comprobado la factura real del proveedor.']
    (directory / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with (directory / 'report.md').open('a', encoding='utf-8') as output:
        output.write('\n## Descargas y controles registrados\n\n')
        for failure in result['fetch_errors']:
            output.write('- ' + str(failure.get('url')) + ': ' + str(failure.get('http_status') or failure.get('code')) + '\n')
        if not result['article_versions']:
            output.write('- No hay versiones redactadas registradas; no se atribuyen controles de calidad a documentos que no se redactaron.\n')
        for version in result['article_versions']:
            output.write('- Versión ' + str(version['version']) + ': ' + str(version['title']).replace('\n', ' ') + '\n')
            output.write('  - Validación determinista: ' + version['deterministic_validation'] + '\n')
            output.write('  - Revisión: ' + json.dumps(version['review'], ensure_ascii=False) + '\n')
        if checks:
            output.write('\n## Publicación y SEO\n\n' + json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
        output.write('\n## Seguimiento necesario\n\n')
        if any(e.get('http_status') == 403 for e in result['fetch_errors']):
            output.write('- Hay fuentes con acceso denegado. Revisar alternativas públicas y verificables; no eludir los 403.\n')
        if result['reason'] == 'budget_exhausted':
            output.write('- El límite económico detuvo el proceso. Revisar consumo y tamaño del flujo sin aumentar automáticamente el presupuesto.\n')
        if result['status'] != 'published':
            output.write('- Revisar el motivo y los controles registrados antes de cualquier nueva publicación; no repetir un cobro o una ejecución automáticamente.\n')
        else:
            output.write('- Revisar los resultados SEO indicados y observar utilidad e indexación; publicación no equivale a tráfico o calidad garantizados.\n')
        if timed_out:
            output.write('- Se alcanzó el límite de observación de las 23:05. Revisar el trabajador y el expediente; el observador no lo reinicia.\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, type=date.fromisoformat)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--check-once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    deadline = datetime.combine(args.date, daytime(23, 5), tzinfo=MADRID)
    timeline, snapshot = [], None
    while True:
        now = datetime.now(UTC)
        try:
            snapshot = capture(args.date.isoformat())
            run = snapshot.get('run') or {}
            timeline.append({'at': now.isoformat(), 'status': run.get('status'), 'reason': run.get('reason'),
                'worker_alive': snapshot['worker_alive'], 'reserved_microusd': run.get('reserved_microusd', 0)})
            finished = bool(run.get('finished_at')) and run.get('status') != 'running'
            expired = now >= deadline
            checks = None
            if finished and run.get('status') == 'published' and snapshot.get('article'):
                try: checks = public_checks(snapshot['article'])
                except Exception as exc: checks = {'not_completed': type(exc).__name__}
            save(args.output, snapshot, timeline, expired and not finished, checks)
            if args.check_once or finished or expired: return
        except Exception as exc:
            timeline.append({'at': now.isoformat(), 'observation_error': type(exc).__name__})
            if now >= deadline or args.check_once:
                save(args.output, snapshot or {'date': args.date.isoformat()}, timeline, True)
                raise
        time.sleep(30)


if __name__ == '__main__':
    main()
