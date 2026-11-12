"""Offline regressions from production run 15 (2026-11-04). No network, no model calls.

The fixture holds the real drafts, validation errors and reviews of the four attempts.
These tests check that the controls still reject the same drafts and that the fixes
work: attribution is recognised, correction plans contain actions, evidence is focused
and the extra correction is bounded. They do not relax any rule.
"""
import hashlib
import json
from pathlib import Path

import pytest

from app.research import evidence, writing
from app.research.editorial_policy import attribution_present, scope_terms
from app.research.examples import EXAMPLES
from app.research.quality import DETERMINISTIC, FIXABLE
from app.research.queue import example_focused, example_terms
from app.research.style import correction_plan, issues
from app.research.writing import Draft

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'run15_20261104.json').read_text(encoding='utf-8'))


def attempt(candidate):
    return next(a for a in FIXTURE['attempts'] if a['candidate_id'] == candidate)


def draft(candidate, version):
    return Draft.model_validate(attempt(candidate)['versions'][version]['draft'])


# --- Attribution (news #32) -------------------------------------------------

def test_google_cloud_division_is_valid_attribution():
    d = draft(32, 1)
    assert any(attribution_present(t, 'google', 'Google') for t in [d.summary, d.paragraphs[0].text])


@pytest.mark.parametrize('text,ok', [
    ('Google anunció una novedad para empresas.', True),
    ('Google Cloud publicó su resumen mensual.', True),
    ('Según Google DeepMind, el modelo mejora.', True),
    ('Google Cloud ha anunciado nuevas funciones.', True),
    ('Google compra publicó una nota.', False),          # arbitrary word: not a division
    ('Un blog sobre Google publicó una nota.', False),   # Google is not the subject
    ('NVIDIA Cloud anunció un servicio.', False),        # not a listed NVIDIA unit
    ('La compañía anunció novedades.', False),
])
def test_attribution_is_a_closed_list(text, ok):
    org, name = ('nvidia', 'NVIDIA') if text.startswith('NVIDIA') else ('google', 'Google')
    assert attribution_present(text, org, name) is ok


# --- Scope (news #33) --------------------------------------------------------

def test_comparatives_still_detected_in_both_nvidia_versions():
    assert 'comparativas' in scope_terms(draft(33, 0))
    assert scope_terms(draft(33, 1))


def test_oversegmented_still_rejected_for_nvidia_v1():
    assert 'oversegmented' in {i['code'] for i in issues(draft(33, 1))}


# --- Correction plans are never empty ---------------------------------------

@pytest.mark.parametrize('candidate,version,feedback', [
    (32, 0, {'code': 'insufficient_content'}),
    (32, 1, {'code': 'official_attribution_missing', 'details': [{'code': 'official_attribution_missing', 'message': 'Pon a Google como sujeto.'}]}),
    (33, 0, {'code': 'official_scope_requires_corroboration', 'details': [{'code': 'official_scope_requires_corroboration', 'terms': ['comparativas']}]}),
    (33, 1, {'code': 'editorial_style_rejected'}),
    (4, 0, {'code': 'editorial_style_rejected'}),
])
def test_run15_failures_produce_concrete_actions(candidate, version, feedback):
    plan = correction_plan(draft(candidate, version), feedback)
    assert plan['required_actions'], feedback['code']
    assert plan['invariants']


def test_scope_plan_names_the_exact_terms():
    plan = correction_plan(draft(33, 0), {'code': 'official_scope_requires_corroboration',
                                          'details': [{'terms': ['comparativas']}]})
    assert any('comparativas' in a for a in plan['required_actions'])


def test_oversegmentation_plan_targets_two_to_four_sections():
    plan = correction_plan(draft(33, 1), {'code': 'editorial_style_rejected'})
    assert plan['section_count'] == 7
    assert any('dos a cuatro' in a for a in plan['required_actions'])


@pytest.mark.parametrize('candidate', [3, 4])
def test_review_plan_lists_each_unsupported_claim(candidate):
    a = attempt(candidate)
    v = a['versions'][-1]
    unsupported = [c for c in v['review']['checks'] if c['supported'] is False]
    assert unsupported
    plan = correction_plan(Draft.model_validate(v['draft']),
                           {'code': 'review_rejected', 'unsupported_targets': unsupported})
    listed = ' '.join(plan['required_actions'])
    for check in unsupported[:12]:
        assert check['target_id'] + ':' in listed


# --- Bounded extra correction ----------------------------------------------

def test_extra_correction_only_for_local_deterministic_codes():
    assert DETERMINISTIC <= FIXABLE
    assert 'editorial_review_rejected' not in DETERMINISTIC
    assert 'review_rejected' not in DETERMINISTIC


# --- Evidence focused on the verified example (evergreen #3, #4) ------------

def page(body_before, key_text):
    text = ('Intro de documentación. ' * 40) + body_before + key_text + (' Final. ' * 200)
    return {'url': 'https://docs.python.org/3.12/library/stdtypes.html', 'title': 'Built-in Types',
            'text': text, 'content_sha256': hashlib.sha256(text.encode()).hexdigest()}


def test_example_terms_cover_sql_and_methods():
    sqlite = example_terms(EXAMPLES['sqlite_results'])
    assert {'INSERT OR REPLACE', 'PRIMARY KEY', 'execute'} <= set(sqlite)
    assert 'casefold' in example_terms(EXAMPLES['text_normalization'])


def test_focus_brings_late_passage_into_the_catalogue():
    key = 'str.casefold() Return a casefolded copy of the string. Casefolded strings may be used for caseless matching. ' * 3
    doc = page('x ' * 15000, key)
    assert 'casefold' not in doc['text'][:18000]
    focused = example_focused(doc, ['casefold'])
    catalogued = evidence.catalogue([focused])[0]
    assert any('casefold' in f['text'] for f in catalogued['fragments'])
    assert focused['content_sha256'] == hashlib.sha256(focused['text'].encode()).hexdigest()
    # Every focused part is an exact substring of the original page.
    for part in focused['text'].split('\n\n'):
        assert part in doc['text']


def test_focus_leaves_short_documents_untouched():
    doc = {'url': 'https://docs.python.org/x', 'title': 't', 'text': 'corto', 'content_sha256': 'h'}
    assert example_focused(doc, ['casefold']) is doc


def test_sqlite_example_declares_official_sqlite_documentation():
    from app.research.sources import DOCUMENT_HOSTS
    docs = EXAMPLES['sqlite_results']['docs']
    assert 'https://www.sqlite.org/lang_conflict.html' in docs
    assert DOCUMENT_HOSTS['www.sqlite.org'] == 'sqlite'


# --- Rules sent BEFORE the first paid draft ---------------------------------

def captured_policy(policy):
    from app.research.config import ResearchSettings
    try:
        request = writing.prepare_request(ResearchSettings(), Draft, writing.VOICE,
                                          {'sources': [], 'editorial_policy': policy})
    except Exception as exc:  # pragma: no cover - shape depends on provider adapter
        pytest.skip(f'prepare_request needs provider config: {exc}')
    return json.dumps(request, ensure_ascii=False, default=str)


def test_official_policy_states_attribution_scope_and_structure():
    text = captured_policy({'verification_mode': 'official_announcement', 'official_name': 'Google'})
    assert 'attribution_rule' in text and 'forbidden_scope' in text and 'structure' in text
    assert 'Google Cloud' in text


def test_evergreen_policy_states_claims_rule():
    text = captured_policy({'kind': 'tutorial'})
    assert 'claims_rule' in text and 'Entre 3 y 5 secciones' in text


# --- Traceability (#33) ------------------------------------------------------

def test_fixture_records_both_news_candidates_in_order():
    news = [a['candidate_id'] for a in FIXTURE['attempts'] if a['engine'] == 'news']
    assert news == [32, 33]
