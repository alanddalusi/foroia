"""Ortotipografía de titulares: mayúscula inicial, tildes interrogativas y siglas.

Solo corrige forma, nunca contenido: no añade ni quita palabras. Se aplica al
título antes de crear el snapshot publicado, de modo que H1, <title>, og:title y
JSON-LD siguen siendo idénticos al título guardado.
"""
import re

# Palabras en minúscula que siempre son siglas o marcas con grafía fija.
FIXED = {
    'ia': 'IA', 'api': 'API', 'apis': 'APIs', 'sdk': 'SDK', 'json': 'JSON', 'csv': 'CSV', 'pdf': 'PDF',
    'pdfs': 'PDFs', 'sql': 'SQL', 'sqlite': 'SQLite', 'http': 'HTTP', 'llm': 'LLM', 'llms': 'LLMs',
    'rag': 'RAG', 'gpt': 'GPT', 'openai': 'OpenAI', 'chatgpt': 'ChatGPT', 'claude': 'Claude',
    'gemini': 'Gemini', 'google': 'Google', 'anthropic': 'Anthropic', 'python': 'Python',
    'fastapi': 'FastAPI', 'pydantic': 'Pydantic', 'unicode': 'Unicode', 'copilot': 'Copilot',
    'microsoft': 'Microsoft', 'nvidia': 'NVIDIA', 'github': 'GitHub',
}
# Interrogativos al inicio del titular («que son…», «como usar…»).
INTERROGATIVE = {'que': 'Qué', 'como': 'Cómo', 'cual': 'Cuál', 'cuales': 'Cuáles', 'cuando': 'Cuándo',
                 'donde': 'Dónde', 'quien': 'Quién', 'cuanto': 'Cuánto', 'cuanta': 'Cuánta'}
WORD = re.compile(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+')


def polish_title(title: str) -> str:
    text = re.sub(r'\s+', ' ', title).strip()
    if not text:
        return text
    # Solo palabras enteramente en minúscula: respeta grafías ya correctas («iOS», «GPT-4o»).
    text = WORD.sub(lambda m: FIXED.get(m.group(0), m.group(0)) if m.group(0).islower() else m.group(0), text)
    first = WORD.search(text)
    if first and first.start() == 0:
        word = first.group(0)
        if word.lower() in INTERROGATIVE and word.islower():
            # «por que» no se toca: puede ser causal; solo interrogativos simples.
            text = INTERROGATIVE[word.lower()] + text[first.end():]
        elif word.islower():
            text = word[0].upper() + word[1:] + text[first.end():]
    return text
