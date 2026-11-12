"""Offline editorial hypotheses; never fabricated SEO demand or regional pages."""
from difflib import SequenceMatcher
from app.research.selection import normalize,STOP

COUNTRIES=['ES','MX','CO','AR','PE','CL']
ALIASES={'json':['JSON','JavaScript Object Notation'],'csv':['CSV','valores separados por comas'],
         'pdf':['PDF','documentos PDF'],'pydantic':['Pydantic','validación de esquemas'],
         'fastapi':['FastAPI','validación de peticiones'],'unicode':['Unicode','normalización de texto']}


def terms(value):return set(normalize(value).split())-STOP-{'como','usar','utilizar','guia','tutorial','respuesta','respuestas','antes','generado','generados'}


def opportunity(candidate,articles,now,verified=False):
    keyword=candidate.keyword.strip();words=terms(keyword+' '+candidate.topic)
    related=[]
    for article in articles:
        other=terms(article.title);overlap=len(words&other)/max(1,len(words|other))
        similarity=SequenceMatcher(None,normalize(candidate.topic),normalize(article.title)).ratio()
        if overlap>=.18 or similarity>=.6:
            related.append({'article_id':article.id,'url':'/articulos/'+article.slug,'title':article.title,'summary':getattr(article,'summary','')[:300],
                'score':round(max(overlap,similarity if similarity>=.78 else 0),3)})
    related=sorted(related,key=lambda r:r['score'],reverse=True)[:5]
    variants=list(dict.fromkeys(alias for word in words for alias in ALIASES.get(word,[])))[:8]
    phrase=keyword.removeprefix('como ').removeprefix('cómo ')
    questions=['¿Cómo '+phrase+'?'] if phrase.split() and phrase.split()[0].endswith(('ar','er','ir')) else []
    urls=[s if isinstance(s,str) else s.get('url') for s in candidate.details.get('evidence',candidate.details.get('sources',[]))]
    from app.research.blueprints import BY_KEY,AI_APPLICATIONS
    blueprint=BY_KEY.get(candidate.details.get('blueprint'))
    engine=getattr(candidate,'engine','evergreen')
    application=AI_APPLICATIONS.get(blueprint.key,'') if blueprint else ''
    legacy=candidate.details.get('demand_source')=='official_document_section_hypothesis'
    assessment={'search_intent':candidate.intent,'practical_application':application or (candidate.intent if engine=='news' else None),
        'site_coverage':{'related_published_articles':len(related),'basis':'Muestra local de títulos publicados; no mide competencia en Google ni experiencia práctica.'},
        'originality':{'status':'overlap_review_needed' if related else 'no_close_title_detected','basis':'Solapamiento léxico local, no análisis semántico completo.'},
        'traffic_potential':{'status':'not_measured','search_volume':None,'basis':'Sin datos de consultas, impresiones o volúmenes importados; no se estima tráfico.'},
        'freshness':{'status':'sources_verified' if verified else 'requires_source_verification','assessed_at':now.isoformat()},
        'example_id':blueprint.example if blueprint else None,
        'editorial_basis':'documentation_heading_only' if legacy else 'named_news_event' if engine=='news' else 'curated_user_problem',
        'requires_editorial_reframing':legacy}
    return {'version':2,'primary_keyword':keyword,'semantic_variants':variants,'related_questions':questions,
        'intent':candidate.intent,'audience':'Personas hispanohablantes que buscan resolver esta tarea; nivel introductorio e intermedio.',
        'target_countries':COUNTRIES,'language':'es','regional_versions':False,'recommended_kind':candidate.kind,
        'related_content':related,'cannibalization_risk':'high' if related and related[0]['score']>=.78 else 'possible' if related else 'low',
        'assessed_at':now.isoformat(),'evidence_urls':[u for u in urls if u][:8],
        'evidence_status':'verified' if verified else 'planned','demand_source':candidate.details.get('demand_source','editorial_hypothesis'),
        'search_volume':None,'seo_difficulty':None,'trend':None,'assessment':assessment,'unavailable_reason':'Dato no disponible: sin API de demanda ni volúmenes medidos.'}
