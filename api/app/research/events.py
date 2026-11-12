"""Conservative named-event rules; no model calls or invented popularity scores."""
import hashlib,re,unicodedata
from datetime import datetime,UTC,timedelta

def normalized(value):
    value=''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))
    return re.sub('[‐‑‒–—−]','-',value)

# Specific product/version names; a bare mention of AI or a company is insufficient.
PRODUCTS=[('openai','models',r'\b(?:gpt[- ]?\d+(?:[.]\d+)*o?(?:[- ]?(?:mini|nano|sol|terra))?|o[134](?:[- ]mini)?|sora(?:[- ]\d+)?)\b'),
 ('tesla','robotics',r'\boptimus\b'),('tesla','autonomy',r'\b(?:cybercab|fsd(?:[- ]v?\d+(?:[.]\d+)*)?)\b'),
 ('nvidia','hardware',r'\b(?:blackwell(?: ultra)?|rubin|jetson(?: thor)?)\b'),('nvidia','robotics',r'\b(?:gr[0o]{2}t(?:[- ]n?\d+(?:[.]\d+)*)?|cosmos)\b'),
 ('google','models',r'\bgemini(?:[- ]\d+(?:[.]\d+)*)?\b'),('meta','models',r'\bllama[- ]\d+(?:[.]\d+)*\b'),
 ('anthropic','models',r'\bclaude(?:[- ](?:opus|sonnet|haiku))?(?:[- ]\d+(?:[.]\d+)*)?\b'),('google','autonomy',r'\bwaymo(?: driver)?\b'),
 ('bostondynamics','robotics',r'\batlas\b')]
ACTIONS=[('update',r'\b(?:updates?|updated|actualiza|actualizacion|upgrade)\b'),
 ('availability',r'\b(?:available|availability|deploys?|deployment|disponible|despliega|expands?|expansion)\b'),
 ('launch',r'\b(?:announc\w*|introduc\w*|unveil\w*|launch\w*|releas\w*|presenta\w*|lanza\w*|anuncia\w*)\b')]

def identify(source):
    title=normalized(source.get('title',''));context=title+' '+normalized(source.get('text','')[:1800])
    found=[]
    for owner,category,pattern in PRODUCTS:
        match=re.search(pattern,title) or re.search(pattern,context)
        if match:found.append((0 if re.search(pattern,title) else 1,owner,category,re.sub(r'[- ]','',match.group()).replace('gr00t','groot')))
    if not found:return None
    if len({(owner,product) for priority,owner,category,product in found if priority==0})>1:return None
    _,owner,category,product=sorted(found)[0]
    # Title verbs outrank body/navigation verbs and avoid treating a stale update as a launch.
    action=next((name for name,pattern in ACTIONS if re.search(pattern,title)),None)
    if not action:
        matches=[(match.start(),name) for name,pattern in ACTIONS if (match:=re.search(pattern,context))]
        action=min(matches)[1] if matches else None
    if not action:return None
    try:
        stamp=datetime.fromisoformat(source.get('published','').replace('Z','+00:00'))
        if stamp.tzinfo is None:return None
    except (ValueError,TypeError,AttributeError):return None
    return {'entity':owner,'product':product,'event':action,'category':category,'date':stamp.astimezone(UTC).date().isoformat()}

def compatible(a,b):
    return bool(a and b and all(a[k]==b[k] for k in ['entity','product','event'])
        and abs(datetime.fromisoformat(a['date'])-datetime.fromisoformat(b['date']))<=timedelta(days=1))

def event_key(event):
    return hashlib.sha256(('event:v1:'+'|'.join(event[k] for k in ['entity','product','event','date'])).encode()).hexdigest()
