"""Execute only our reviewed public examples; never call a provider or read keys."""
import importlib.util
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace as Event

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'web/public/recursos/api-ia' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STREAM = load('streaming_texto')
CLAUDE = load('primera_peticion_claude')


def test_streaming_preserves_deltas_and_ignores_unknown_events():
    written = []
    events = [Event(type='response.created'), Event(type='future.event'),
              Event(type='response.output_text.delta', delta='Hola '),
              Event(type='response.output_text.delta', delta='mundo'),
              Event(type='response.completed')]
    assert STREAM.consume_text(events, written.append) == 'Hola mundo'
    assert written == ['Hola ', 'mundo']


@pytest.mark.parametrize('kind', ['error', 'response.failed', 'response.incomplete', None])
def test_partial_stream_is_never_treated_as_completed(kind):
    events = [Event(type='response.output_text.delta', delta='Texto parcial')]
    if kind:
        events.append(Event(type=kind))
    with pytest.raises(ValueError):
        STREAM.consume_text(events, lambda text: None)


def test_stream_limit_and_invalid_delta():
    for delta, limit in [('12345', 4), (None, 100)]:
        with pytest.raises(ValueError):
            STREAM.consume_text([Event(type='response.output_text.delta', delta=delta)], lambda _: None, limit)


@pytest.mark.parametrize('failure', [False, True])
def test_stream_request_closes_resource_even_after_failure(failure):
    events = [Event(type='error')] if failure else [Event(type='response.completed')]
    closed, requests = [], []
    class Stream:
        def __iter__(self):
            return iter(events)
        def close(self):
            closed.append(True)
    def create(**kwargs):
        requests.append(kwargs)
        return Stream()
    client = Event(responses=Event(create=create))
    if failure:
        with pytest.raises(ValueError):
            STREAM.stream_text(client, 'test-model', 'Question', lambda _: None)
    else:
        assert STREAM.stream_text(client, 'test-model', 'Question', lambda _: None) == ''
    assert closed == [True]
    assert requests == [dict(model='test-model', input='Question', stream=True, max_output_tokens=1000)]


def test_claude_request_contract_filters_nontext_blocks():
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return Event(stop_reason='end_turn', content=[Event(type='thinking'), Event(type='text', text='Respuesta')])
    client = Event(messages=Event(create=create))
    assert CLAUDE.request_text(client, 'test-model', 'Question') == 'Respuesta'
    assert calls == [dict(model='test-model', max_tokens=256, messages=[dict(role='user', content='Question')])]


@pytest.mark.parametrize('reason', ['max_tokens', 'tool_use', 'refusal', 'pause_turn'])
def test_claude_nonfinal_or_other_workflows_are_not_a_text_success(reason):
    client = Event(messages=Event(create=lambda **_: Event(stop_reason=reason, content=[Event(type='text', text='Parcial')])))
    with pytest.raises(ValueError):
        CLAUDE.request_text(client, 'test-model', 'Question')


def test_claude_requires_text():
    client = Event(messages=Event(create=lambda **_: Event(stop_reason='end_turn', content=[])))
    with pytest.raises(ValueError):
        CLAUDE.request_text(client, 'test-model', 'Question')


REVISIONS = list((ROOT / 'docs/content-revisions/2026-11-09').glob('*.json'))


@pytest.mark.parametrize('path', REVISIONS, ids=lambda p: p.stem)
def test_content_revision_is_guarded_and_preserves_identity(path):
    from app.modules.articles.schemas import ArticleWrite
    change = json.loads(path.read_text(encoding='utf-8'))
    before, after = change['before'], change['after']
    assert change['state'] == 'local_review_only_not_applied'
    assert hashlib.sha256(json.dumps(before, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == change['expected_before_sha256']
    ArticleWrite.model_validate(after)
    for field in ['slug', 'title', 'summary', 'section', 'author_name']:
        assert after[field] == before[field]
    assert [s['url'] for s in before['sources']] == [s['url'] for s in after['sources'][:len(before['sources'])]]
    assert all('--- title:' not in s['title'] and 'llms.txt' not in s['title'] for s in after['sources'])
    assert not any(field.endswith('_at') for field in after)
    assert not re.search(r'[a-z]+\?[a-z]+', after['body'], re.I)
    for link in re.findall(r'\]\((/[^)]+)\)', after['body']):
        if link.startswith('/recursos/'):
            assert (ROOT / 'web/public' / link.lstrip('/')).is_file()


def test_pydantic_article_has_an_executed_acceptance_and_rejection_example():
    change = next(json.loads(p.read_text(encoding='utf-8')) for p in REVISIONS if p.stem.startswith('validar-respuestas'))
    blocks = re.findall(r'```python\n(.*?)```', change['after']['body'], re.S)
    namespace = {}
    # Two reviewed, local-only blocks: schema followed by its exact reader test.
    assert len(blocks) == 2
    for block in blocks:
        exec(compile(block, '<reviewed-pydantic-article>', 'exec'), namespace)


def revised_namespace(slug):
    change = json.loads((ROOT / 'docs/content-revisions/2026-11-09' / (slug + '.json')).read_text(encoding='utf-8'))
    code = re.findall(r'```python\n(.*?)```', change['after']['body'], re.S)
    assert len(code) == 1
    namespace = {}
    exec(compile(code[0], '<reviewed-tutorial>', 'exec'), namespace)
    return namespace


def test_fastapi_reader_example_checks_normalized_text_not_only_raw_length():
    import asyncio
    import httpx
    namespace = revised_namespace('fastapi-validar-peticiones-ia')
    async def verify():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=namespace['app']), base_url='http://test') as client:
            assert (await client.post('/prepare', json={'text': '  Idea  '})).json() == {'text': 'Idea'}
            for payload in [{'text': ''}, {'text': '   '}, {'text': 'x' * 501}, {'text': 'Idea', 'extra': True}]:
                assert (await client.post('/prepare', json=payload)).status_code == 422
    asyncio.run(verify())


def test_json_reader_example_rejects_types_before_string_operations():
    parse = revised_namespace('validar-json-ia-python')['parse_response']
    assert parse('{"resumen":"Idea"}') == 'Idea'
    for raw in [None, 1, {}, b'{"resumen":"Idea"}']:
        with pytest.raises(TypeError):
            parse(raw)
    for raw in ['{', '[]', '{"resumen":8}', 'x' * 10001]:
        with pytest.raises(ValueError):
            parse(raw)
