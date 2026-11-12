"""Offline capacity model. No HTTP, credentials, database or publication calls.

This models two or three publication slots; it does not prove editorial success.
Successful stages and available evidence are scenario assumptions. Costs come
from anonymized reported API usage, not independently verified provider bills.
"""
import argparse
import calendar
import json
from pathlib import Path
from statistics import median


def simulate(samples, caps, *, daily, monthly, days=30, stressed=False, multiplier=1, practical_articles=1, corrections=1):
    if min(daily, monthly, days, multiplier) <= 0:
        raise ValueError('Positive budgets, days and multiplier required')
    choose = max if stressed else lambda values: int(median(values))
    observed = {stage: choose(values) * multiplier for stage, values in samples.items()}
    schedule = [('shared', 'NewsResearch', 'search')]
    if stressed:
        schedule.append(('news', 'SourceRecovery', 'search'))
    if practical_articles not in (1,2):raise ValueError('One or two practical articles')
    lanes=['news',*[f'practical{i}' for i in range(1,practical_articles+1)]]
    for lane in lanes:
        key='news' if lane=='news' else 'practical'
        schedule.extend([(lane, 'Draft', key + '_draft'), (lane, 'Review', key + '_review')])
        if stressed:
            if corrections not in (1,2):raise ValueError('At most two corrections')
        for _ in range(corrections if stressed else 0):
            schedule.extend([(lane, 'Draft', key + '_correction'), (lane, 'Review', key + '_review')])
    spent = 0
    published = 0
    records = []
    for day in range(1, days + 1):
        today = 0
        successes = dict.fromkeys(lanes,True)
        peaks = []
        blocked = []
        for lane, stage, cap_key in schedule:
            if lane != 'shared' and not successes[lane]:
                continue
            # No negative settlement if a historical cost exceeds a sample cap.
            reserve = max(caps[cap_key] * multiplier, observed[stage])
            if today + reserve > daily or spent + reserve > monthly:
                blocked.append({'lane': lane, 'stage': stage, 'required': reserve})
                if lane == 'shared':
                    successes['news'] = False
                else:
                    successes[lane] = False
                continue
            peaks.append(today + reserve)
            # This branch assumes confirmed complete usage and exact settlement.
            today += observed[stage]
            spent += observed[stage]
        count = sum(successes.values())
        published += count
        records.append({'day': day, 'accounted_microusd': today,
                        'peak_daily_reservation': max(peaks, default=0),
                        'hypothetical_articles': count, 'blocked': blocked})
    return {'days': days, 'daily_limit': daily, 'monthly_limit': monthly,
            'accounted_microusd': spent, 'remaining_microusd': monthly - spent,
            'hypothetical_articles': published, 'planned_articles': days * len(lanes),
            'assumes_valid_evidence_and_successful_quality_checks': True,
            'billing_verified': False, 'records': records}


def unknown_charge_then_practical(caps, daily):
    """An ambiguous search retains its ENTIRE reservation; never settle to zero."""
    held = caps['search']
    needed = caps['practical_draft'] + caps['practical_review']
    return {'unknown_reservation': held, 'practical_headroom': needed,
            'practical_can_start': held + needed <= daily}


def monthly_daily_allowance(daily, monthly_remaining, year, month, day):
    """A monthly ceiling must also cover 31-day months, without increasing it."""
    left = calendar.monthrange(year, month)[1] - day + 1
    return min(daily, max(0, monthly_remaining) // left)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path('tests/fixtures/editorial_capacity_20261104.json'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--practical-articles',type=int,choices=(1,2),default=1)
    parser.add_argument('--corrections',type=int,choices=(1,2),default=1)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
    result = {'simulation_only': True, 'api_calls': 0, 'real_publications': 0,
              'sample_calls': sum(map(len, fixture['samples'].values())), 'scenarios': {}}
    budgets=[(500000,15000000)] if args.practical_articles==2 else [(200000,10000000),(400000,12000000)]
    for daily, monthly in budgets:
        for name, stress, factor in [('median', False, 1), ('observed_max_with_corrections', True, 1),
                                     ('cost_sensitivity_2x', True, 2)]:
            result['scenarios'][f'{daily / 1000000:.2f}/{monthly / 1000000:.0f}:{name}'] = simulate(
                fixture['samples'], fixture['caps'], daily=daily, monthly=monthly,
                stressed=stress, multiplier=factor,practical_articles=args.practical_articles,corrections=args.corrections)
    result['unknown_charge'] = unknown_charge_then_practical(fixture['caps'], 200000)
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(encoded, encoding='utf-8')
    else:
        print(encoded)


if __name__ == '__main__':
    main()
