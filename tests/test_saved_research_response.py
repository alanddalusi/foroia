"""Optional private real-response replay. No provider and no production writes."""
import json
from pathlib import Path
import pytest
from app.research import writing,evidence
from app.research.config import ResearchSettings

SAVED=Path('.local/deploy/manual-20261025-current.json')

@pytest.mark.skipif(not SAVED.exists(),reason='Private saved real response unavailable')
def test_real_saved_drafts_have_resolvable_evidence_without_paid_calls():
    saved=json.loads(SAVED.read_text())['run']['report']['candidate_attempts'][0]['report']
    sources=saved['evidence_catalogue'];evidence.index(sources)
    for version in saved['versions']:
        draft=writing.Draft.model_validate(version['draft'])
        policy=saved['policy']
        result=writing.validate_draft(draft,sources,[],policy,provisional=True)
        assert result.title==draft.title and result.sources
        _,data,payload,_,_,_,maximum=writing.prepare_request(ResearchSettings().model_copy(update={'max_output_tokens':4000}),writing.Review,writing.REVIEW_INSTRUCTIONS,{'sources':sources,'draft':draft.model_dump(),'editorial_policy':policy})
        offered={f['fragment_id'] for s in data['sources'] for f in s['fragments']}
        assert maximum<150000
        old=version['review']
        unknown=[fid for check in old['checks'] for fid in check['fragment_ids'] if fid not in offered]
        # Real historical responses also contained guessed/empty identifiers.
        # The new decoder must forbid them, rather than treating them as evidence.
        assert unknown
        allowed=payload['text']['format']['schema']['$defs']['EvidenceCheck']['properties']['fragment_ids']['items']['enum']
        assert all(fid not in allowed for fid in unknown)
        assert len({check['target_id'] for check in old['checks']})==len(data['targets'])
        # Never change the historical rejection into a synthetic approval.
        assert old['approved'] is False
