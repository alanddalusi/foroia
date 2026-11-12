"""Ortotipografía de titulares: solo forma, nunca palabras nuevas."""
import pytest
from app.research.title_style import polish_title


@pytest.mark.parametrize('raw,expected', [
    ('que son embeddings ia y cómo usarlos para buscar texto', 'Qué son embeddings IA y cómo usarlos para buscar texto'),
    ('function calling openai python: qué es y cómo compararlo', 'Function calling OpenAI Python: qué es y cómo compararlo'),
    ('error 429 api openai: cómo mantener tu aplicación estable', 'Error 429 API OpenAI: cómo mantener tu aplicación estable'),
    ('como usar GPT-4o en iOS', 'Cómo usar GPT-4o en iOS'),
    # Títulos ya correctos no cambian.
    ('Qué anunció Google Cloud en IA este mes', 'Qué anunció Google Cloud en IA este mes'),
    ('Comparar respuestas IA: normalizar Unicode en Python', 'Comparar respuestas IA: normalizar Unicode en Python'),
])
def test_polish_title(raw, expected):
    assert polish_title(raw) == expected
    assert polish_title(expected) == expected
    assert len(polish_title(raw).split()) == len(raw.split())


def test_pipeline_keeps_draft_title_verbatim():
    """Incidente 09/11/2026: corregir el título dentro de validate_draft rompió la
    comparación de borradores reanudados (article_changed). Solo se corrige tras publicar."""
    import inspect
    from app.research import writing
    assert 'polish_title' not in inspect.getsource(writing)


@pytest.mark.parametrize('number,support,expected', [
    ('1.000.000', 'Prices are listed per 1M tokens.', True),
    ('1.000.000', 'USD per million input tokens', True),
    ('1,000,000', 'precio por millón de tokens', True),
    ('128.000', 'a 128K context window', True),
    ('2.000', '2 thousand requests', True),
    ('1.000.000', 'a 1 m cable', False),          # «m» suelta no es «millón»
    ('1.500.000', 'per 1M tokens', False),        # solo múltiplos exactos
    ('2026', '2025 annual report', False),
])
def test_magnitude_equivalences_are_closed(number, support, expected):
    from app.research.numbers import supported_number
    assert supported_number(number, support) is expected


def test_base64_is_an_identifier_not_a_claim():
    """Incidente 09/11/2026: «Base64» se leyó como la cifra 64 y tumbó #46 y #48."""
    from app.research.numbers import factual_numbers
    assert factual_numbers('Envía la imagen en Base64 o como URL; admite 20 imágenes.') == ['20']
    assert factual_numbers('El modelo procesa 64 imágenes.') == ['64']


def test_consumer_help_centres_are_registered_and_planned():
    """Herramientas para usuarios (11/11/2026): centros de ayuda oficiales, nunca help.openai.com (403)."""
    from app.research.sources import DOCUMENT_HOSTS, HOSTS
    from app.research.blueprints import BY_KEY, AI_APPLICATIONS
    assert DOCUMENT_HOSTS['support.google.com'] == 'google' and DOCUMENT_HOSTS['support.claude.com'] == 'anthropic'
    assert 'help.openai.com' not in DOCUMENT_HOSTS and len([h for h in HOSTS if h]) <= 100
    for key in ('gemini-apps-start', 'claude-start', 'claude-pro-plan'):
        assert BY_KEY[key].section == 'herramientas' and key in AI_APPLICATIONS
