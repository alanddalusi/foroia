"""Financial model only; these tests do not prove two-lane publication works."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('capacity', ROOT / 'scripts/simulate_editorial_capacity.py')
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)
DATA = json.loads((ROOT / 'tests/fixtures/editorial_capacity_20261104.json').read_text())


def test_observed_costs_can_fund_both_lanes_but_do_not_prove_content_quality():
    for daily, monthly in [(200000, 10000000), (400000, 12000000)]:
        result = capacity.simulate(DATA['samples'], DATA['caps'], daily=daily, monthly=monthly, stressed=True)
        assert result['hypothetical_articles'] == 60
        assert result['accounted_microusd'] <= monthly
        assert all(r['peak_daily_reservation'] <= daily for r in result['records'])
        assert result['assumes_valid_evidence_and_successful_quality_checks']


def test_budget_exhaustion_blocks_calls_and_never_goes_negative():
    result = capacity.simulate(DATA['samples'], DATA['caps'], daily=200000, monthly=120000, stressed=True)
    assert result['accounted_microusd'] <= 120000
    assert result['remaining_microusd'] >= 0
    assert result['hypothetical_articles'] < 60
    assert any(r['blocked'] for r in result['records'])


def test_uncertain_search_keeps_full_reservation_and_practical_headroom():
    result = capacity.unknown_charge_then_practical(DATA['caps'], 200000)
    assert result['unknown_reservation'] == DATA['caps']['search']
    assert result['practical_can_start']
    assert not capacity.unknown_charge_then_practical(DATA['caps'], 55000)['practical_can_start']


def test_31_days_and_previously_spent_monthly_budget_are_respected():
    assert capacity.monthly_daily_allowance(400000, 12000000, 2026, 12, 1) == 387096
    assert capacity.monthly_daily_allowance(400000, 0, 2026, 12, 31) == 0
    result = capacity.simulate(DATA['samples'], DATA['caps'], daily=400000, monthly=12000000,
                               days=31, stressed=True, multiplier=2)
    assert result['accounted_microusd'] <= 12000000
