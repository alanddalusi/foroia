from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/research_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sample():
    return {'date': '2026-10-24', 'configuration': {'daily_usd': '0.15', 'monthly_usd': '5'},
        'monthly_reserved_microusd': 200000, 'worker_alive': True,
        'run': {'status': 'skipped', 'reason': 'insufficient_sources', 'reserved_microusd': 0,
            'report': {'feed_count': 3, 'candidate_count': 9, 'sources': [{}, {}],
                'fetch_failures': 1, 'fetch_errors': [{'url': 'https://openai.com/index/example', 'http_status': 403}]}}}


def test_report_distinguishes_documents_from_generated_articles():
    result = audit.summarize(sample(), [])
    assert result['candidate_document_count'] == 9 and result['recovered_documents'] == 2
    assert result['article_versions'] == [] and result['public_checks'] is None
    assert result['daily_within_limit'] and result['monthly_within_limit']
    assert result['fetch_errors'][0]['http_status'] == 403


def test_report_preserves_failed_and_corrected_quality_reviews():
    snapshot = sample()
    snapshot['run']['report']['versions'] = [
        {'draft': {'title': 'First version'}, 'validation_error': 'invalid_evidence'},
        {'draft': {'title': 'Corrected version'}, 'review': {'approved': True, 'supported': True}}]
    result = audit.summarize(snapshot, [])
    assert result['article_versions'][0]['deterministic_validation'] == 'invalid_evidence'
    assert result['article_versions'][0]['review'] == 'not_evaluated_or_not_recorded'
    assert result['article_versions'][1]['deterministic_validation'] == 'passed'


def test_report_flags_budget_excess_and_writes_private_evidence(tmp_path):
    snapshot = sample()
    snapshot['run']['reserved_microusd'] = 150001
    snapshot['monthly_reserved_microusd'] = 5000001
    result = audit.summarize(snapshot, [])
    assert not result['daily_within_limit'] and not result['monthly_within_limit']
    audit.save(tmp_path, snapshot, [], True)
    assert '403' in (tmp_path/'report.md').read_text(encoding='utf-8')
    assert (tmp_path/'snapshot.json').is_file()


def test_page_parser_reads_ssr_metadata_and_json_ld():
    page = audit.Page('<title>Guide</title><meta name="description" content="Example"><link rel="canonical" href="https://foroiaaldia.com/articulos/example"><h1>Guide &amp; sources</h1><script type="application/ld+json">[{"@type":"BlogPosting"}]</script>')
    assert page.title == 'Guide' and page.h1 == 'Guide & sources'
    assert page.canonical == ['https://foroiaaldia.com/articulos/example']
    assert page.schemas[0][0]['@type'] == 'BlogPosting'
