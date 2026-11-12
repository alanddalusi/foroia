"""Event queries and curated official entry points; search results are not evidence."""
import hashlib
import json
import re
from decimal import ROUND_CEILING
from pydantic import BaseModel,ConfigDict,Field
from app.research import sources
from app.research.news_gate import entities,signal
from app.research.selection import normalize

from app.research.editorial_policy import OFFICIAL
INDEXES={
    'amd':('https://ir.amd.com/news-events/press-releases','https://newsroom.amd.com/all-news/'),
    'oracle':('https://www.oracle.com/news/',),
    'openai':('https://openai.com/news/company-announcements/',),
    'nvidia':('https://nvidianews.nvidia.com/news/latest',),
    'microsoft':('https://devblogs.microsoft.com/foundry/',),
    'anthropic':('https://www.anthropic.com/news',),
    'google':('https://blog.google/technology/ai/',),
    'xai':('https://x.ai/company',),
    'meta':('https://ai.meta.com/blog/',),
    'tesla':('https://ir.tesla.com/press',),
}
STOP=set('anuncio anuncios announcement announcements fecha date publicado publicacion published recap resumen listado cobertura medios seguimiento comunicado released registrados publicos explicacion relevancia tecnologicas tecnologico nuevas nuevos nueva nuevo tecnologias herramientas para sobre como con por del las los una uno unos unas entre que sus this that from with will into como ampliacion avance avances'.split())

class RecoveredLinks(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event_id:str
    urls:list[str]=Field(min_length=1,max_length=6)
    reason:str=Field(min_length=1,max_length=1000)

class RecoveryResult(BaseModel):
    model_config=ConfigDict(extra='forbid')
    candidates:list[RecoveredLinks]=Field(max_length=3)
    search_summary:str=Field(max_length=2000)
    empty_reason:str=Field(max_length=1000)
    discarded:list[str]=Field(max_length=10)

def event_id(item):
    value='|'.join([normalize(item.title),normalize(item.event),item.date])
    return 'event_'+hashlib.sha256(value.encode()).hexdigest()[:24]

def query(item,independent=False):
    text=item.title+' '+item.event
    names=sorted(entities(text))
    products=re.findall(r'\b(?:devday|helios|epyc|codex|chatgpt|rubin|blackwell|genie|grok|voice|s[- ]?1|q[1-4]|gpt[- ]?\d+(?:[.]\d+)*|20\d\d)\b',text.lower())
    aliases={'ipo':'IPO filing','devday':'DevDay recap','earnings':'earnings results','partnership':'partnership collaboration','grok_voice':'Grok Voice release'}
    terms=list(dict.fromkeys([*names,*products,aliases.get(signal(text),'')]))
    if len([t for t in terms if t])<4:
        terms.extend(t for t in normalize(item.title).split() if len(t)>3 and t not in STOP and t not in names)
    terms=list(dict.fromkeys(t for t in terms if t))[:12]
    return ' '.join(terms)+' '+item.date+(' independent reporting announcement' if independent else ' official announcement')

def plan(item):
    return {'event_id':event_id(item),'title':item.title,'date':item.date,
        'organization':item.organization,'official_query':query(item),
        'independent_query':query(item,True)}

def entrypoints(item):
    return list(dict.fromkeys(u for org in sorted(entities(item.title+' '+item.event)) for u in INDEXES.get(org,())))[:3]

def search_payload(config,now,titles,items):
    from app.research.night_web import payload,strict_schema
    from app.research.writing import request_payload
    request=payload(config,now,titles)
    request['instructions']='''Recupera fuentes alternativas para los acontecimientos proporcionados.
La URL inicial puede estar bloqueada o ser un agregador. Busca el comunicado original
y cobertura independiente del MISMO acontecimiento usando empresa, producto, fecha y
términos de cada consulta. No investigues temas nuevos ni repitas búsquedas generales.
No eludas 403, paywalls ni bloqueos. Devuelve solo artículos individuales HTTPS de los
dominios permitidos. Un comunicado sindicado sigue perteneciendo a su emisor.
Usa únicamente los event_id proporcionados; devuelve sus urls y explica qué documentos
encontraste en reason. No vuelvas a generar títulos, fechas ni entidades. Si no hay documentos,
omite el candidato y explica el descarte. Las respuestas y snippets no son evidencia:
el servidor descargará y verificará contenido, fecha y autoría antes de redactar.
Usa como máximo una llamada web_search; prioriza las consultas indicadas en su orden.'''
    request['input']=json.dumps({'queries':[plan(i) for i in items[:3]],
        'candidates':[i.model_dump() for i in items[:3]],'already_published_titles':titles},ensure_ascii=False)
    request['tools'][0]['filters']={'allowed_domains':sorted(h for h in sources.HOSTS if h)[:100]}
    request['text']=request_payload(config,RecoveryResult,'',{})['text']
    request['text']['format']['name']='sourcerecovery'
    schema=request['text']['format']['schema'];strict_schema(schema)
    schema['$defs']['RecoveredLinks']['properties']['event_id']['enum']=[event_id(i) for i in items[:3]]
    schema['$defs']['RecoveredLinks']['properties']['urls']['items']['pattern']=r'^https://[^\s<>]+$'
    return request

def drafting_headroom(config):
    # Two ordinary calls (draft/review), with 64k total input-token allowance.
    # A minimum safety margin, not a promise that any article fits that size.
    return int((64000*config.input_per_million+2*config.max_output_tokens*config.output_per_million).to_integral_value(rounding=ROUND_CEILING))

async def search(db,run,config,redis,token,now,items,provider=None):
    """One durable, budgeted fallback per run attempt; no uncertain retries."""
    from app.research.night_web import research
    if not items:return [],{'state':'not_needed'}
    factory=lambda c,n,t:search_payload(c,n,t,items)
    originals={event_id(i):i for i in items[:3]}
    def decode(row):
        if not isinstance(row,dict) or set(row)!={'event_id','urls','reason'} or row.get('event_id') not in originals:return row
        return dict(originals[row['event_id']].model_dump(),urls=row['urls'],reason=row['reason'])
    candidates,report=await research(db,run,config,redis,token,now,provider,
        state_key='alternative_web_research',request_factory=factory,
        stage='SourceRecovery',headroom_microusd=drafting_headroom(config),candidate_decoder=decode)
    report=dict(report,minimum_drafting_microusd=drafting_headroom(config))
    if report.get('state')=='unfunded':return [],dict(report,reason='recovery_budget_headroom')
    if not report.get('settled') or report.get('observed_tool_limit_exceeded'):
        return [],dict(report,reason='uncertain_search_result' if not report.get('settled') else 'unexpected_search_count')
    return candidates,report
