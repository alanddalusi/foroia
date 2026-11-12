"""Regressions from the paid 25/10 run, with public/synthetic identifiers only."""
import json
from test_evidence_first import grounded,approved_payload
from test_research import EVIDENCE
from app.research import evidence,writing
from app.research.config import ResearchSettings


def contracts():
    sources=evidence.catalogue(EVIDENCE)
    draft=grounded(sources)
    resolved=writing.resolve_grounded(draft,sources)
    data={'sources':evidence.model_sources(sources),'draft':resolved.model_dump(),'targets':evidence.targets(resolved)}
    review=writing.request_payload(ResearchSettings(),writing.GroundedReview,writing.REVIEW_INSTRUCTIONS,data)
    writing.evidence_contract(review,data,sources,writing.Review,{})
    generation_data={'sources':evidence.model_sources(sources)}
    generation=writing.request_payload(ResearchSettings(),writing.GroundedDraft,writing.GROUNDED_INSTRUCTIONS,generation_data)
    writing.evidence_contract(generation,generation_data,sources,writing.Draft,{})
    return sources,draft,data,review,generation


def test_generator_schema_cannot_choose_a_plausible_but_unknown_fragment():
    sources,draft,data,review,generation=contracts()
    offered={f['fragment_id'] for s in generation_data_sources(generation) for f in s['fragments']}
    enumeration=generation['text']['format']['schema']['$defs']['EvidenceRef']['properties']['fragment_id']['enum']
    assert set(enumeration)==offered and 'e_'+'f'*32 not in enumeration


def generation_data_sources(payload):return json.loads(payload['input'])['sources']


def test_review_decoder_allows_correction_only_from_offered_fragments():
    sources,draft,data,review,generation=contracts()
    shape=review['text']['format']['schema']
    offered={f['fragment_id'] for s in generation_data_sources(review) for f in s['fragments']}
    assert set(shape['$defs']['EvidenceCheck']['properties']['fragment_ids']['items']['enum'])==offered
    checks=shape['properties']['checks']
    assert set(checks['required'])=={t['target_id'] for t in data['targets']}
    assert checks['additionalProperties'] is False


def test_valid_review_matches_every_decoder_branch():
    sources,draft,data,review,generation=contracts()
    valid=approved_payload(review)
    allowed=review['text']['format']['schema']['$defs']['EvidenceCheck']['properties']['fragment_ids']['items']['enum']
    for check in valid['checks']:
        assert set(check['fragment_ids'])<=set(allowed)
