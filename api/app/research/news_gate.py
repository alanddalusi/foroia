"""Local event correspondence before corroboration; no model or network calls."""
import re
from app.research.selection import normalize,features,relationship
from app.research.events import PRODUCTS,normalized

COMPANIES={
 'anthropic':r'\b(?:anthropic|claude)\b','openai':r'\b(?:openai|gpt[- ]?\d|devday)\b',
 'google':r'\b(?:google|alphabet|gemini|deepmind)\b','nvidia':r'\b(?:nvidia|rubin|blackwell)\b',
 'microsoft':r'\b(?:microsoft|copilot|foundry)\b','xai':r'\b(?:xai|x[.]ai|grok)\b',
 'tesla':r'\b(?:tesla|optimus|cybercab)\b','meta':r'\b(?:meta|llama|muse)\b',
 'deepseek':r'\bdeepseek\b','oracle':r'\b(?:oracle|oci)\b','amd':r'\b(?:amd|epyc|helios)\b'}
COMPANY_WORDS=set('anthropic claude openai google alphabet gemini deepmind nvidia microsoft copilot foundry xai grok tesla optimus meta llama muse oracle noticias news official company inteligencia artificial model modelo'.split())

def entities(text):
    return {org for org,pattern in COMPANIES.items() if re.search(pattern,normalized(text))}

def signal(text):
    t=normalize(text)
    if re.search(r'\b(?:ipo|initial public offering|salida a bolsa|s 1)\b',t):return 'ipo'
    if 'devday' in t:return 'devday'
    if re.search(r'\b(?:earnings|resultados|q[1-4])\b',t):return 'earnings'
    if 'copilot harness' in t:return 'copilot_harness'
    if 'voice' in t and 'grok' in t:return 'grok_voice'
    if re.search(r'\b(?:partnership|collaboration|alianza|asociacion|colaboracion)\b',t):return 'partnership'
    return None

def matches(item,document):
    title=item['title'] if isinstance(item,dict) else item.title
    event=item.get('event','') if isinstance(item,dict) else item.event
    target=title+' '+event
    focus=document.get('title','')+' '+document.get('text','')[:1400]
    wanted=entities(target);found=entities(document.get('title','')) or entities(focus)
    if not found and document.get('organization_verified') and document.get('organization') in COMPANIES:
        found={document['organization']}
    if wanted and found and not wanted & found:
        return {'related':False,'code':'document_unrelated','basis':'different_entities','target_entities':sorted(wanted),'document_entities':sorted(found)}
    wanted_signal=signal(target)
    if wanted_signal:
        matched=signal(focus)==wanted_signal and (not wanted or bool(wanted & found))
        if wanted_signal=='partnership':
            # A joint announcement needs the named parties, not a different
            # collaboration involving just one of the same companies.
            matched=matched and len(wanted & entities(focus))>=min(2,len(wanted))
            products=set(re.findall(r'\b(?:helios|epyc|codex|chatgpt)\b',normalized(target)))
            if products:matched=matched and bool(products & set(normalized(focus).split()))
        if wanted_signal=='grok_voice':
            version=re.search(r'voice\s+(\d+(?:[.]\d+)*)',normalized(target))
            if version:matched=matched and bool(re.search(r'voice\s+'+re.escape(version[1])+r'\b',normalized(focus)))
        if wanted_signal=='earnings':
            quarter=re.search(r'\b(q[1-4])\s+(20\d\d)\b',normalize(target))
            if quarter:matched=matched and bool(re.search(r'\b'+quarter[1]+r'\s+'+quarter[2]+r'\b',normalize(focus)))
        return {'related':matched,'code':'event_match' if matched else 'document_unrelated','basis':wanted_signal,
            'target_entities':sorted(wanted),'document_entities':sorted(found)}
    target_products={re.sub(r'[- ]','',m.group()) for _,_,pattern in PRODUCTS for m in re.finditer(pattern,normalized(target))}
    if target_products:
        in_focus=re.sub(r'[- ]','',normalized(focus))
        matched=any(product in in_focus for product in target_products) and (not wanted or bool(wanted & found))
        return {'related':matched,'code':'event_match' if matched else 'document_unrelated','basis':'named_product','products':sorted(target_products)}
    # No company name alone can nominate or corroborate an event.
    probe={'title':title,'text':event}
    a,ac=features(probe);b,bc=features({'title':document.get('title',''),'text':document.get('text','')[:4000]})
    shared=(a & b)-COMPANY_WORDS
    concepts=(ac & bc)-{'initial_public_offering'}
    matched=bool(concepts) or len(shared)>=2
    return {'related':matched,'code':'event_match' if matched else 'document_unrelated','basis':'specific_topic',
        'shared_anchors':sorted(shared),'concepts':sorted(concepts)}


def retrieval_hint(item,title):
    """A headline is a retrieval hint only, never sufficient evidence.

    Related headlines first; bounded same-entity alternatives may reveal the
    event in their article body. Full correspondence still runs after download.
    """
    if matches(item,{'title':title,'text':''})['related']:return 2
    target=(item['title']+' '+item.get('event','')) if isinstance(item,dict) else item.title+' '+item.event
    return int(bool(entities(target)&entities(title)))

def initial_filing_key(text):
    """Narrow duplicate check for the demonstrated initial-filing regression.

    Prices, amendments and other later IPO developments are different events.
    """
    t=normalize(text)
    if signal(text)!='ipo' or re.search(r'\b(?:amend\w*|modifica\w*|actualiza\w*|precio|price|pricing|update\w*)\b',t):return None
    if not re.search(r'\b(?:fil\w*|present\w*|registr\w*|documentacion|s 1)\b',t):return None
    orgs=entities(text)
    return next(iter(orgs))+':initial_filing' if len(orgs)==1 else None
