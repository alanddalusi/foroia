"""Editorial checks on prose, never a replacement for evidence review."""
import re
from collections import Counter
from difflib import SequenceMatcher
from app.research.selection import normalize

STYLE_FLAGS = ('natural', 'non_repetitive', 'well_structured', 'attribution_clear')
REVIEW_FLAGS = ('approved','supported','useful','original','spanish','no_invented_experience','safe_topic',*STYLE_FLAGS)


def review_feedback(verdict):
    flags={k:verdict.get(k) is True for k in REVIEW_FLAGS}
    failed=[k for k,v in flags.items() if not v]
    return {'code':'editorial_review_rejected' if any(not flags[k] for k in STYLE_FLAGS) else 'review_rejected',
        'reasons':verdict.get('reasons') or ['Fallaron estos controles obligatorios: '+', '.join(failed)+'.'],
        'editorial_checks':{k:flags[k] for k in STYLE_FLAGS}, 'review_checks':flags,
        'unsupported_targets':[c for c in verdict.get('checks',[]) if not c.get('supported')][:20]}
INSTRUCTIONS = '''
Redacta como una redacción tecnológica profesional: español natural, preciso y fluido,
sin fingir ser una persona ni haber probado productos. Titular informativo, entradilla,
desarrollo y contexto útil cuando las fuentes lo permitan. Explica qué ocurrió, por qué
importa, cómo funciona y a quién afecta sin inventar lo que no está documentado.
Los encabezados describen el contenido, no comienzan por «Según [empresa]».
Identifica la fuente al presentar el anuncio; repite atribuciones solo para distinguir
promesas comerciales, rendimiento, beneficios, previsiones o resultados no contrastados.
No empieces sistemáticamente los párrafos por Según, La compañía o una fórmula similar.
Varía la sintaxis; evita traducciones literales, frases duplicadas, relleno y apartados
artificialmente breves. Para una noticia breve suelen bastar dos o tres secciones;
no crees seis apartados cuando tres resuelvan el tema. Las guías largas pueden necesitar más.
Las citas privadas siguen respaldando cada afirmación aunque no repitas la atribución visible.
El titular describe una necesidad concreta o un acontecimiento; no conviertas etiquetas
de documentación como Input, Constraints o Choosing a model en títulos «Uso de ... con ...».
No basta con traducir un índice de documentación: resuelve la tarea editorial proporcionada,
añade contexto que las fuentes permitan y explica los límites. No añadas palabras para SEO.
En tutoriales de Python, JSON u otras herramientas, la aplicación a la IA debe ser explícita
y útil. No prometas tráfico, búsquedas populares ni pruebas de producto que no se han medido.
Usa editorial_opportunity para delimitar la necesidad y diferenciar el artículo de los
títulos y resúmenes relacionados que se proporcionan. No inventes el contenido completo
de esos artículos ni afirmes conocer su tráfico o posiciones. Aprovecha enlaces internos
pertinentes; si no hay información para aportar una diferencia útil, no rellenes.
'''


def issues(draft):
    found=[]
    headings=[normalize(p.heading) for p in draft.paragraphs]
    texts=[normalize(p.text) for p in draft.paragraphs]
    if any(re.match(r'^(?:segun|de acuerdo con)\b',h) for h in headings):
        found.append({'code':'attribution_headings','message':'Describe el contenido en los encabezados; elimina las fórmulas de atribución iniciales.'})
    openers=[' '.join(t.split()[:3]) for t in texts]
    if any(n>=3 for n in Counter(openers).values()):
        found.append({'code':'repeated_opening','message':'Varía el inicio de los párrafos; no repitas la misma fórmula.'})
    attributed=sum(bool(re.match(r'^(?:segun|de acuerdo con)\b',t)) for t in texts)
    if attributed>=2 and attributed*2>=len(texts):
        found.append({'code':'repeated_attribution','message':'Presenta la fuente una vez y reserva la atribución adicional para afirmaciones que lo necesiten.'})
    if any(SequenceMatcher(None,a,b).ratio()>=.90 for i,a in enumerate(texts) for b in texts[i+1:]):
        found.append({'code':'repeated_paragraph','message':'Elimina párrafos duplicados o casi idénticos.'})
    if len(texts)>=5 and sum(len(t.split()) for t in texts)<350:
        found.append({'code':'oversegmented','message':'Agrupa los apartados breves relacionados en menos secciones con desarrollo suficiente.'})
    return found


def validate(draft):
    from app.research.writing import StopRun
    errors=issues(draft)
    if errors:raise StopRun('editorial_style_rejected',errors)


def correction_plan(draft, feedback):
    """Concrete editing instructions from local measurements, never new facts.

    Every rejection code yields actions (run 15 sent four corrections with an empty
    list), plus invariants so fixing one problem does not create another.
    """
    local = issues(draft)
    words = sum(len(normalize(p.text).split()) for p in draft.paragraphs)
    code = feedback['code']
    details = feedback.get('details') or []
    actions = []
    structured_rejection=feedback.get('editorial_checks',{}).get('well_structured') is False
    if any(e['code']=='oversegmented' for e in local) or (structured_rejection and len(draft.paragraphs)>=5) or len(draft.paragraphs)>=6:
        actions.append(f'Reduce las {len(draft.paragraphs)} secciones a dos a cuatro, fusionando las relacionadas (por ejemplo, ejemplos con casos de uso). Cada sección debe desarrollar su idea con al menos 70 palabras. No añadas relleno. Conserva hechos, evidencias y ejemplos verificados.')
    if any(e['code'] in {'attribution_headings','repeated_attribution'} for e in local):
        actions.append('Reescribe los encabezados para describir su contenido; presenta la fuente al inicio y conserva atribución donde delimita promesas o datos no contrastados.')
    if any(e['code'] in {'repeated_opening','repeated_paragraph'} for e in local):
        actions.append('Fusiona las ideas duplicadas y cambia las aperturas repetidas, sin sustituirlas por otra muletilla.')
    if code=='insufficient_content':
        actions.append(f'El cuerpo tiene {words} palabras y es insuficiente. Amplía con información que esté en los fragmentos: qué se anuncia exactamente, cómo funciona, a quién afecta y qué no aclara la fuente. No acortes ninguna sección ni repitas ideas.')
    if code=='official_attribution_missing':
        message=next((d.get('message') for d in details if d.get('code')=='official_attribution_missing'),None)
        actions.append(message or 'Empieza el resumen y el primer párrafo nombrando a la organización como sujeto: «X anunció…».')
    if code=='official_scope_requires_corroboration':
        terms=sorted({t for d in details for t in d.get('terms',[])})
        actions.append('Elimina o reformula sin comparaciones, rumores ni litigios estos términos: '+(', '.join(terms) if terms else 'los señalados')+'. Describe lo anunciado sin valorarlo frente a otros productos.')
    if code in {'editorial_review_rejected','review_rejected'}:
        actions.append('Resuelve cada motivo concreto del revisor en el texto; no basta con cambiar citas o signos de puntuación.')
        checks=feedback.get('review_checks') or {}
        if checks.get('original') is False:
            actions.append('Replantea la explicación para resolver la tarea concreta con un enfoque propio y ejemplos verificados; evita reproducir la estructura de la documentación o artículos relacionados.')
        if checks.get('useful') is False:
            actions.append('Centra el texto en la tarea y aplicación a IA previstas; elimina consejos ajenos a las evidencias en vez de añadir secciones de relleno.')
        if checks.get('supported') is False:
            actions.append('Elimina las afirmaciones sin apoyo que no puedas reformular con los fragmentos disponibles. No basta con anteponer «recomendamos» a una afirmación factual sin evidencia.')
        unsupported=feedback.get('unsupported_targets') or []
        if unsupported:
            from app.research.evidence import targets
            texts={t['target_id']:t['text'] for t in targets(draft)}
            listed=[f"{u['target_id']}: «{texts.get(u['target_id'],'')[:160]}»" for u in unsupported[:12]]
            actions.append('Estas afirmaciones no tienen respaldo en los fragmentos. Para cada una: reescríbela para decir solo lo que dice un fragmento, apóyala en otro fragmento disponible o en el ejemplo verificado, o elimínala. Una recomendación propia debe presentarse como recomendación, no como hecho documentado. Afirmaciones: '+' | '.join(listed))
            if any(u['target_id'] in {'title','summary'} for u in unsupported):
                actions.append('El título y el resumen no pueden prometer más de lo que demuestran las secciones respaldadas; ajústalos al contenido final.')
    invariants=[f'Mantén al menos {max(words,260)} palabras de cuerpo salvo que elimines afirmaciones sin respaldo.' if code!='insufficient_content' else 'El cuerpo final debe superar 250 palabras.',
        'Usa entre dos y cuatro secciones en noticias y hasta cinco en guías.','No introduzcas comparaciones, rumores ni datos nuevos sin fragmento.']
    return {'section_count':len(draft.paragraphs),'prose_words':words,
            'headings':[p.heading for p in draft.paragraphs], 'local_issues':local,
            'required_actions':actions,'invariants':invariants,
            'acceptance':'Debe superar nuevamente la validación local y la revisión completa; no se aprueba por agotar intentos.'}
