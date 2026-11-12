"""Server-derived scope for official announcements; model labels grant no trust."""
import re
import hashlib
from datetime import datetime, timedelta

from app.research.selection import normalize, organization

OFFICIAL = frozenset({'openai','anthropic','google','nvidia','microsoft','meta','tesla','xai','deepseek','oracle','huggingface','ai2','amd'})
OFFICIAL_SCOPE = 'Report the organization’s announcement faithfully. Identify the official source in the lead; attribute unverified commercial claims, performance, benefits, forecasts and results where needed. Do not imply independent testing or corroboration.'
STRICT = re.compile(r'\b(?:rumou?rs?|leaks?|leaked|filtracion\w*|rumor\w*|acusacion\w*|accus\w*|alleg\w*|lawsuit|demanda judicial|demanda contra|demandad[oa]s?|versus|vs(?! code\b)|comparacion\w*|comparativ\w*|comparison\w*|comparar|compare[ds]?)\b')
ANNOUNCEMENT = re.compile(r'\b(?:announc\w*|introduc\w*|launch\w*|releas\w*|present\w*|anunci\w*|lanz\w*|unveil\w*|disponib\w*|available|partnership|alianza|devday|files|filing|s 1)\b')


def official_source(source):
    org = organization(source)
    if org not in OFFICIAL or source.get('retrieval_method') != 'page':
        return False
    if source.get('event_correspondence', {}).get('related') is not True:
        return False
    # These are collector-validated original bytes, not snippets, a blocked URL,
    # syndicated text or a model-provided provenance label.
    if source.get('content_sha256') != hashlib.sha256(source.get('text','').encode()).hexdigest() or len(source.get('text', '')) < 500:
        return False
    try:
        published = datetime.fromisoformat(source['published'])
        retrieved = datetime.fromisoformat(source['retrieved_at'])
        if not published.tzinfo or not retrieved.tzinfo:
            return False
        calendar = source.get('published_precision') in {'calendar_day','publisher_index_calendar_day','sec_filing_calendar_day'}
        timely = ((retrieved-timedelta(hours=48)).date() <= published.date() <= retrieved.date()) if calendar else timedelta(minutes=-5) <= retrieved-published <= timedelta(hours=48)
        if not timely:
            return False
    except (KeyError, ValueError, TypeError):
        return False
    origin = source.get('content_origin')
    if origin and origin.rstrip('/') != source['url'].rstrip('/'):
        return False
    title = normalize(source['title'])
    from app.research.news_gate import entities
    named = entities(source['title'])
    if named and org not in named:
        return False
    return bool(ANNOUNCEMENT.search(title+' '+normalize(source['text'][:800]))) and not STRICT.search(title+' '+normalize(source.get('announcement_scope', '')))


def policy_for(evidence):
    orgs = {organization(s) for s in evidence} - {None}
    official = [s for s in evidence if official_source(s)]
    if len(orgs) == 1 and official and all(official_source(s) for s in evidence):
        org = next(iter(orgs))
        name = {'openai':'OpenAI','anthropic':'Anthropic','google':'Google','nvidia':'NVIDIA','microsoft':'Microsoft','meta':'Meta','tesla':'Tesla','xai':'xAI','deepseek':'DeepSeek','oracle':'Oracle','huggingface':'Hugging Face','ai2':'AI2','amd':'AMD'}[org]
        return {'verification_mode':'official_announcement','min_organizations':1,
                'official_organization':org,'official_name':name,'editorial_style_version':1,
                'scope':OFFICIAL_SCOPE}
    return {'verification_mode':'independently_corroborated','min_organizations':2,'editorial_style_version':1}


# Named units of the SAME organization only ("Google Cloud publicó"). A closed list:
# an arbitrary word between the name and the verb is not accepted as attribution.
DIVISIONS = {'google':('cloud','deepmind','research','ai','for developers'),'microsoft':('research','azure','ai'),
             'nvidia':('research','ai'),'meta':('ai','fair'),'openai':(),'anthropic':(),'tesla':('ai',),
             'xai':(),'deepseek':(),'oracle':('cloud',),'huggingface':(),'ai2':(),'amd':()}
VERBS = r'(?:ha |han )?(?:anunci\w*|present\w*|lanz\w*|public\w*|comunic\w*|afirm\w*|asegur\w*|explic\w*|indic\w*|sosten\w*|sostien\w*|describ\w*|declar\w*)'


def attribution_present(text, organization, name):
    """Explicit attribution in the opening of a text: '<org> [división] anunció…' or 'según <org>'."""
    first = normalize(text)[:220]
    name = normalize(name)
    unit = '|'.join(re.escape(d) for d in DIVISIONS.get(organization, ()))
    subject = re.escape(name) + (r'(?: (?:' + unit + r'))?' if unit else '')
    return bool(re.search(r'\b(?:segun|de acuerdo con|en palabras de) ' + subject + r'\b', first) or
                re.search(r'\b(?:procede|proviene) (?:del|de la) (?:blog|comunicado|documentacion|nota|publicacion) oficial de '+subject+r'\b',first) or
                # The organization must be the subject, not the object of a preposition
                # («un blog sobre Google publicó…» is not attribution).
                re.search(r'(?<!sobre )(?<!de )(?<!del )(?<!en )(?<!con )(?<!a )\b' + subject + r' ' + VERBS + r'\b', first))


def scope_terms(draft):
    """Exact words that turn an official announcement into a claim needing corroboration."""
    text = normalize(draft.title + ' ' + draft.summary + ' ' + ' '.join(p.heading + ' ' + p.text for p in draft.paragraphs))
    # A limitation is not an objective comparison. The grounded reviewer must
    # still verify the statement; this only avoids the local lexical false alarm.
    text=re.sub(r'\b(?:sin|no (?:aporta|incluye|presenta)) (?:evaluaciones |mediciones |pruebas )?comparativas?\b',' ',text)
    return sorted({m.group(0) for m in STRICT.finditer(text)})


def validate_scope(draft, evidence, policy):
    from app.research.writing import StopRun
    if policy.get('verification_mode') != 'official_announcement':
        return
    verified = policy_for(evidence)
    if verified.get('verification_mode') != 'official_announcement' or verified['official_organization'] != policy.get('official_organization'):
        raise StopRun('invalid_official_announcement')
    org, name = verified['official_organization'], verified['official_name']
    if not any(attribution_present(text, org, name) for text in [draft.summary, draft.paragraphs[0].text]):
        raise StopRun('official_attribution_missing', [{'code': 'official_attribution_missing',
            'message': f'La primera frase del resumen o del primer párrafo debe tener a {name} como sujeto con un verbo de comunicación, por ejemplo «{name} anunció…» o «Según {name}, …».'}])
    terms = scope_terms(draft)
    if terms:
        raise StopRun('official_scope_requires_corroboration', [{'code': 'official_scope_requires_corroboration',
            'terms': terms, 'message': 'Un anuncio oficial sin fuente independiente no puede presentar comparaciones, rumores ni litigios. Elimina o reformula: ' + ', '.join(terms) + '.'}])
