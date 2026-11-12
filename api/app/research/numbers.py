"""Literal claim tokens, distinct from list labels and HTTP code families."""
import re

TOKEN = re.compile(r'(?<!\d)(?:[45][xX]{2}(?!\w)|\d+(?:[.,]\d+)*)')
# Registered names whose digits are part of the identifier: sqlite3 (Python module) and
# base64 (encoding named by the OpenAI/Anthropic image and PDF docs; 09/11/2026 it was
# misread as a claim of «64» and rejected #46/#48). Not a general alphanumeric exemption.
IDENTIFIER = re.compile(r'\b(?:sqlite3|base64)\b',re.I)
# Closed list of magnitude spellings used by pricing/limit docs («1M tokens», «per million»).
# (unit, compact letter written attached to the figure, words that may follow a space)
MAGNITUDES = ((1_000_000, 'm', r'(?:million|millions|millón|millon|millones)'), (1_000, 'k', r'(?:thousand|mil)'))


def literal_tokens(text):
    # sqlite3 is the registered Python module name, not a claim of three
    # rows/models/retries. Its existence and behavior still need semantic
    # evidence. Do not exempt arbitrary alphanumeric quantities or versions.
    identifiers=[m.span() for m in IDENTIFIER.finditer(text)]
    return [m for m in TOKEN.finditer(text) if not any(a<=m.start()<b for a,b in identifiers)]


def factual_numbers(text):
    # Only a complete, consecutive enumeration earns this exemption. A lone
    # '(20)' or a measured quantity never becomes a decorative list label.
    markers = list(re.finditer(r'(?<!\w)(?:\((\d{1,2})\)|(\d{1,2})\))\s+(?=[^\W\d_])', text))
    excluded = set()
    labels = [int(m[1] or m[2]) for m in markers]
    if len(labels) >= 2 and labels == list(range(1, len(labels) + 1)):
        excluded = {m.span(1 if m[1] else 2) for m in markers}
    return [m[0].lower() for m in literal_tokens(text) if m.span() not in excluded]


def supported_number(number, text):
    """Full tokens only: 4xx != 4, 119 != 11, separators may be localized."""
    tokens = {m[0].lower() for m in literal_tokens(text)}
    number = number.lower()
    if number in tokens or number.translate(str.maketrans('.,', ',.')) in tokens:
        return True
    if re.fullmatch(r'[1-9]\d{0,2}(?:\.\d{3})+', number) and number.replace('.', '') in tokens:
        return True
    return magnitude_supported(number, text)


def magnitude_supported(number, text):
    """«1.000.000» ⇔ «1M» / «1 million» / «per million»; «128.000» ⇔ «128K». Exact multiples only."""
    if not re.fullmatch(r'[1-9]\d{0,2}(?:[.,]\d{3})+|[1-9]\d{3,}', number):
        return False
    value = int(re.sub(r'[.,]', '', number)); lower = text.lower()
    for unit, letter, words in MAGNITUDES:
        if value % unit:
            continue
        count = value // unit
        end = r'(?![a-záéíóúñ])'
        if re.search(rf'(?<![\d.,]){count}{letter}{end}', lower) or re.search(rf'(?<![\d.,]){count}\s?{words}{end}', lower):
            return True
        if count == 1 and re.search(rf'\b(?:per|por|a|each|cada)\s+(?:{words}|1{letter}){end}', lower):
            return True
    return False
