"""Versioned, bounded evidence catalogue built without a language model."""
import hashlib
import re
from datetime import UTC, datetime


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def catalogue(sources):
    """Keep exact offsets/text; changing content changes the version and fragment IDs."""
    result = []
    for source in sources:
        text = source['text'][:18_000]
        key = 's_' + digest(source['url'])[:24]
        version = digest(text)
        fragments = []
        start = 0
        while start < len(text):
            end = min(start + 380, len(text))
            if end < len(text):
                boundary = text.rfind(' ', start + 180, end)
                if boundary > start:
                    end = boundary
            excerpt = text[start:end]
            if len(excerpt.strip()) >= 40:
                fragments.append({'fragment_id': 'e_' + digest(f'{key}:{version}:{start}:{end}')[:32],
                    'start': start, 'end': end, 'text': excerpt})
            start = end
            if start < len(text) and text[start] == ' ':
                start += 1
        if fragments:
            result.append(dict(source, text=text, source_key=key, content_sha256=version,
                retrieved_at=source.get('retrieved_at') or datetime.now(UTC).isoformat(),
                fragments=fragments, evidence_version=1))
    return result


def index(sources):
    """Reject tampered catalogues rather than trusting a stored/model supplied flag."""
    result = {}
    for source in sources:
        text = source['text']
        key = 's_' + digest(source['url'])[:24]
        version = digest(text)
        if source.get('source_key') != key or source.get('content_sha256') != version:
            raise ValueError('evidence_source_changed')
        for fragment in source['fragments']:
            start, end = fragment['start'], fragment['end']
            fid = 'e_' + digest(f'{key}:{version}:{start}:{end}')[:32]
            if (not 0 <= start < end <= len(text) or text[start:end] != fragment['text']
                    or fragment['fragment_id'] != fid or fid in result):
                raise ValueError('evidence_fragment_changed')
            result[fid] = (source, fragment)
    return result


def model_sources(sources, required_numbers=()):
    index(sources)
    # Bounded, balanced context; avoid one long document consuming the daily budget.
    result = [dict({k: v for k, v in s.items() if k not in {'text', 'fragments','sections'}}, fragments=[]) for s in sources]
    remaining = 24_000  # UTF-8 bytes of excerpts; reserve() still bounds the ENTIRE payload.
    from app.research.numbers import supported_number
    # Reviews must see the literal passages needed for numeric citations even
    # when a long manual would otherwise exhaust the balanced context first.
    ordered=[]
    for source in sources:
        priority=[]
        for token in dict.fromkeys(required_numbers):
            match=next((f for f in source['fragments'] if supported_number(token,f['text'])),None)
            if match and match not in priority:priority.append(match)
        ordered.append(priority+[f for f in source['fragments'] if f not in priority])
    for position in range(max((len(rows) for rows in ordered), default=0)):
        for rows, target in zip(ordered, result):
            if position >= len(rows):
                continue
            fragment = rows[position]
            size = len(fragment['text'].encode('utf-8'))
            if size <= remaining:
                target['fragments'].append(fragment)
                remaining -= size
    return [s for s in result if s['fragments']]


def targets(draft, numeric=False):
    """Every title, summary, heading and sentence gets an explicit review target."""
    result = [{'target_id': 'title', 'text': draft.title}, {'target_id': 'summary', 'text': draft.summary}]
    for i, paragraph in enumerate(draft.paragraphs, 1):
        result.append({'target_id': f'p{i}.heading', 'text': paragraph.heading})
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡0-9])', paragraph.text)
        result.extend({'target_id': f'p{i}.s{j}', 'text': sentence} for j, sentence in enumerate(sentences, 1))
    if numeric:
        from app.research.numbers import factual_numbers
        # Extra constrained pointers supplement (never replace) the exhaustive
        # semantic review. No number elsewhere in the corpus approves a claim.
        areas=[('title',draft.title),('summary',draft.summary),
               *[(f'p{i}',p.heading+' '+p.text) for i,p in enumerate(draft.paragraphs,1)]]
        for area,text in areas:
            for j,token in enumerate(dict.fromkeys(factual_numbers(text)),1):
                result.append({'target_id':f'{area}.number{j}',
                    'text':f'Comprueba el valor o identificador {token} en {area} y su contexto; no basta que aparezca en otro tema.',
                    'required_numeric_token':token})
    return result
