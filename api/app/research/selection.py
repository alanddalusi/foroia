"""Conservative, offline topic/provenance gate before any generation call.

Semantic equivalences are explicit and versioned, not inferred search demand or a
claim of general language understanding. Ambiguous relationships fail closed.
"""
import hashlib
import re
import unicodedata
from itertools import combinations
from urllib.parse import urlsplit

VERSION = 1
PUBLISHERS = {'openai.com': 'openai', 'blog.google': 'google',
              'www.microsoft.com': 'microsoft', 'blogs.nvidia.com': 'nvidia',
              'deepmind.google':'google','www.anthropic.com':'anthropic','ai.meta.com':'meta',
              'www.tesla.com':'tesla','ir.tesla.com':'tesla','waymo.com':'google','nvidianews.nvidia.com':'nvidia'}
STOP = set('the a an and or of for to in with on by from is are this that how new ai artificial intelligence model models agent agents research researchers microsoft openai google nvidia hugging face release announcement el la los las un una de del para por con en inteligencia artificial modelo modelos agente agentes nuevo nueva investigacion'.split())
CONCEPTS = {
    'initial_public_offering': ('initial public offering', 'proposed initial public offering', 'salida a bolsa', 'ipo', 'form s-1'),
    'local_inference': ('local inference', 'inferencia local', 'on-device inference', 'on device inference', 'used locally', 'ejecucion local'),
    'retrieval_augmented_generation': ('retrieval augmented generation', 'retrieval-augmented generation', 'generacion aumentada por recuperacion'),
    'structured_output': ('structured output', 'salida estructurada', 'salidas estructuradas', 'json schema'),
    'database_agent_training': ('database grading', 'terminal database state', 'entrenamiento de agentes de bases de datos'),
    'interactive_visualization': ('interactive data visualization', 'visualizaciones de datos interactivas'),
    'literature_ideation': ('research ideation', 'ideacion cientifica', 'literature landscape'),
}


def normalize(text):
    return ' '.join(re.findall(r'[a-z0-9]+', ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))))


def organization(source):
    """Verified publisher identity, never an arbitrary host/claimed label."""
    if source.get('organization_verified') is not True:
        return None
    try:
        parts = urlsplit(source['url'])
        valid = parts.scheme == 'https' and not parts.username and not parts.password and parts.port in (None,443)
    except ValueError:
        return None
    if not valid:
        return None
    from app.research.sources import NEWS_HOSTS
    expected = PUBLISHERS.get(parts.hostname) or NEWS_HOSTS.get(parts.hostname)
    if parts.hostname in {'sec.gov','www.sec.gov'}:
        from app.research.sources import sec_issuer
        expected=sec_issuer(source['url'],source.get('text',''))
    if parts.hostname == 'huggingface.co':
        from app.research.sources import HF_ORGANIZATIONS
        path = parts.path.strip('/').split('/')
        if len(path) == 2 and path[0] == 'blog':
            expected = 'huggingface'
        elif len(path) == 3 and path[0] == 'blog' and path[1] in HF_ORGANIZATIONS:
            expected = HF_ORGANIZATIONS[path[1]][0]
    return expected if expected == source.get('organization') else None


def features(source):
    title = normalize(source['title'])
    body = normalize(source.get('text', '')[:18_000])
    anchors = {t for t in title.split() if len(t) >= 4 and t not in STOP}
    concepts = {key for key, aliases in CONCEPTS.items() if any(
        (' '+normalize(a)+' ') in (' '+title+' ') or (' '+body+' ').count(' '+normalize(a)+' ') >= 2 for a in aliases)}
    return anchors, concepts


def relationship(left, right):
    a, ac = features(left); b, bc = features(right)
    shared = a & b
    # Shared product/topic names plus contextual overlap, or a specific bilingual concept.
    context_a = set(normalize(left.get('text', '')).split()) - STOP
    context_b = set(normalize(right.get('text', '')).split()) - STOP
    overlap = len(context_a & context_b) / max(1, min(len(context_a), len(context_b)))
    concepts = ac & bc
    if 'initial_public_offering' in concepts and not (shared-{'initial','public','offering','files','proposed','documentos','presenta','salida','bolsa'}):
        concepts=concepts-{'initial_public_offering'}
    related = bool(concepts) or (len(shared) >= 2 and overlap >= .18) or (bool(shared) and overlap >= .35)
    # RSS titles may nominate a fetch; they never constitute final corroboration.
    preliminary = not left.get('text') or not right.get('text')
    if preliminary and (len(shared) >= 2 or any(len(t) >= 6 for t in shared)):
        related = True
    from app.research.events import identify,compatible
    left_event,right_event=identify(left),identify(right)
    # A deep editorial reference to the exact original announcement is stronger
    # provenance than overlapping generic words. Copy/origin checks still apply.
    direct_reference=left.get('url') in right.get('references',[]) or right.get('url') in left.get('references',[])
    if direct_reference and not preliminary:related=True
    if left_event and right_event:related=compatible(left_event,right_event)
    elif not preliminary and (left_event or right_event):
        event=left_event or right_event;other=right if left_event else left
        product=re.sub(r'[- ]','',normalize(other.get('title','')+' '+other.get('text','')))
        if event['product'] not in product:related=False
    return {'related': related, 'shared_anchors': sorted(shared), 'concepts': sorted(concepts),
            'context_overlap': round(overlap, 3), 'preliminary': preliminary,'direct_reference':direct_reference}


def duplicate(left, right):
    origin_a = left.get('content_origin') or left['url']
    origin_b = right.get('content_origin') or right['url']
    if origin_a.rstrip('/') == origin_b.rstrip('/'):
        return 'same_origin'
    a, b = normalize(left.get('text', '')), normalize(right.get('text', ''))
    if a == b:
        return 'identical_content'
    def shingles(text):
        words = text.split()
        return {' '.join(words[i:i+7]) for i in range(max(0, len(words)-6))}
    aa, bb = shingles(a), shingles(b)
    if min(len(aa), len(bb)) >= 15 and len(aa & bb) / min(len(aa), len(bb)) >= .65:
        return 'reproduced_content'
    return None


def select(sources):
    from app.research.editorial_policy import policy_for
    ordered = sorted(sources, key=lambda s: s['url'])[:8]
    clean, decisions = [], []
    for source in ordered:
        org = organization(source)
        reason = None if org else 'unverified_or_inconsistent_organization'
        if len(source.get('text','').strip()) < 500:
            reason = 'insufficient_document_content'
        match = next(((old, duplicate(old, source)) for old in clean if duplicate(old, source)), None) if not reason else None
        if match:
            reason = match[1]
        if reason:
            decisions.append({'source_id': source['id'], 'url': source['url'], 'reason': reason,
                              'duplicate_of': match[0]['id'] if match else None})
        else:
            clean.append(source)
    groups, seen = [], set()
    for seed in clean:
        group = [seed]
        for candidate in clean:
            if candidate is not seed and all(relationship(candidate, s)['related'] for s in group):
                group.append(candidate)
        key = tuple(sorted(s['url'] for s in group))
        if key in seen:
            continue
        seen.add(key)
        orgs = sorted({organization(s) for s in group})
        topic = 't_' + hashlib.sha256('|'.join(key).encode()).hexdigest()[:24]
        policy = policy_for(group)
        eligible_group = len(orgs) >= policy['min_organizations']
        groups.append({'topic_id': topic, 'title': seed['title'][:200], 'source_ids': [s['id'] for s in group], 'organizations': orgs,
            'verification_mode': policy['verification_mode'],
            'status': 'eligible' if eligible_group else 'rejected',
            'reason': 'verified_official_announcement' if eligible_group and policy['min_organizations']==1 else 'related_independent_evidence' if eligible_group else 'insufficient_independent_topic_sources',
            'relations': [{'left': a['id'], 'right': b['id'], **relationship(a,b)} for a,b in combinations(group, 2)]})
    eligible = sorted((g for g in groups if g['status']=='eligible'), key=lambda g: (-len(g['organizations']), g['topic_id']))
    selected = []
    if eligible:
        chosen = eligible[0]
        # One representative per organization prevents a prolific publisher dominating the prompt.
        used = set()
        for source in clean:
            org = organization(source)
            if source['id'] in chosen['source_ids'] and org not in used:
                selected.append(source); used.add(org)
        # Keep the collector's ordering for resumable drafts and public reference ordering.
        positions = {s['url']: i for i,s in enumerate(sources)}
        selected.sort(key=lambda s: positions[s['url']])
        chosen['status'] = 'selected'
    else:
        chosen = None
    return selected, {'version': VERSION, 'candidates': groups, 'excluded_documents': decisions,
        'selected_topic_id': chosen['topic_id'] if chosen else None,
        'verification_mode': policy_for(selected)['verification_mode'] if selected else None,
        'selected_source_ids': [s['id'] for s in selected], 'selected_organizations': sorted({organization(s) for s in selected}),
        'rejected_candidates': sum(g['status']=='rejected' for g in groups),
        # This daily pipeline has at most one first drafting call, not one per RSS item.
        'generation_calls_avoided': int(not selected),
        'candidate_drafts_suppressed': sum(g['status']=='rejected' for g in groups),
        'generation_calls_started': 0}
