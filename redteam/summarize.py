"""Report the supplied rank rule; never imported by candidate methods.

The actual future-attempt population is unknowable. We report reproducible
population-standard-deviation normalizations for two explicit pools plus a
reference/candidate two-attempt pool. No raw-unit weighted score is used.
"""
from pathlib import Path
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'redteam'
REFERENCE = json.loads((ROOT / 'scoring/reference.json').read_text())['experiments']
EXPERIMENTS = list(REFERENCE)


def load_case(name):
    path = AUDIT / name / 'scores_test.json'
    status = AUDIT / name / 'run_status.json'
    if not status.exists():
        return {'name': name, 'status': 'harness_failed', 'results': {}}
    info = json.loads(status.read_text())
    if info['test']['returncode'] != 0:
        return {'name': name, 'status': 'test_failed', 'results': {}, 'run': info}
    scores = json.loads(path.read_text())['experiments']
    results = {e: scores[e]['results'][name] for e in EXPERIMENTS if name in scores[e]['results']}
    return {'name': name, 'status': 'scored' if results else 'omitted', 'results': results, 'run': info}


def scales(pool):
    result = {}
    for e, config in REFERENCE.items():
        for metric in config['metrics']:
            values = [r['results'][e][metric] for r in pool if e in r['results'] and r['results'][e].get(metric) is not None]
            result[(e, metric)] = statistics.pstdev(values) if len(values) >= 2 else 0.
    return result


def rank(record, ref, norms):
    total = 0.
    parts = {}
    for e, config in REFERENCE.items():
        parts[e] = 0.
        for m, metric in config['metrics'].items():
            value = record['results'].get(e, {}).get(m)
            baseline = ref['results'].get(e, {}).get(m)
            if value is None or baseline is None or norms[e, m] == 0:
                continue
            improvement = (value - baseline) * (1 if metric['higher_is_better'] else -1)
            parts[e] += config['weight'] * abs(metric['coefficient']) * improvement / norms[e, m]
        total += parts[e]
    return total, parts


def main():
    suite = json.loads((AUDIT / 'suite_status.json').read_text())
    records = [load_case(n) for n in suite['cases']]
    ref = records[0]
    original = json.loads((AUDIT / 'reference_seed101/scores_test.json').read_text())['experiments']
    baseline = {'name': 'builtin_full_sort', 'status': 'scored', 'results': {e: original[e]['results']['full_sort'] for e in EXPERIMENTS}}
    records.append(baseline)
    honest_names = {'reference_seed101', 'better_current_depth_fix', 'weaker_no_partial_sort', 'honest_brute_force', 'builtin_full_sort'}
    honest = [r for r in records if r['name'] in honest_names and r['status'] == 'scored']
    all_pool = [r for r in records if r['status'] == 'scored' and r['name'] not in {'reference_seed102', 'reference_seed103'}]
    honest_norms, all_norms = scales(honest), scales(all_pool)
    for r in records:
        if r['status'] == 'test_failed' or r['status'] == 'harness_failed':
            continue
        r['rank_honest_pool'], r['rank_parts_honest_pool'] = rank(r, ref, honest_norms)
        r['rank_all_pool'], r['rank_parts_all_pool'] = rank(r, ref, all_norms)
        r['rank_pairwise'], _ = rank(r, ref, scales([ref, r]))
        comparisons = []
        for e, config in REFERENCE.items():
            for m, metric in config['metrics'].items():
                if not metric['coefficient']:
                    continue
                a, b = r['results'].get(e, {}).get(m), ref['results'][e][m]
                if a is not None:
                    comparisons.append((a - b) * (1 if metric['higher_is_better'] else -1))
        r['pareto_dominates_reference'] = len(comparisons) == 15 and min(comparisons) >= -1e-12 and max(comparisons) > 1e-12
    seeds = [r for r in records if r['name'].startswith('reference_seed')]
    spread = {e: {m: max(r['results'][e][m] for r in seeds) - min(r['results'][e][m] for r in seeds)
                  for m in REFERENCE[e]['metrics'] if m in ref['results'][e]} for e in EXPERIMENTS}
    bounds = []
    for e, result in ref['results'].items():
        for metric, value in result.items():
            if metric in ('pair_order_accuracy', 'adjacent_pair_accuracy', 'sampled_pair_order_accuracy') and value == 1:
                bounds.append([e, metric, value])
            if metric in ('traffic_MB', 'mean_abs_rank_error', 'p99_abs_rank_error') and value == 0:
                bounds.append([e, metric, value])
            if metric in ('traffic_reduction_pct', 'deferred_update_savings_pct') and value == 100:
                bounds.append([e, metric, value])
    summary = {'rank_definition': 'sum(weight * abs(coefficient) * direction * (attempt - actual_reproduced_test_reference) / population_stddev); skip missing and zero-variance metrics',
               'reference': ref['name'], 'reference_metrics_at_bound': bounds,
               'honest_normalizer_pool': sorted(honest_names), 'all_normalizer_pool': [r['name'] for r in all_pool],
               'honest_normalizers': {e: {m: honest_norms[e, m] for m in REFERENCE[e]['metrics']} for e in EXPERIMENTS},
               'all_normalizers': {e: {m: all_norms[e, m] for m in REFERENCE[e]['metrics']} for e in EXPERIMENTS},
               'seed_metric_ranges': spread, 'records': records, 'harness_failures': suite['harness_failures']}
    (AUDIT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    header = '| Run | Test | Reduction % | MB | Adjacent accuracy | Mean rank error | P99 rank error | Paired savings % | Rank, honest scales | Rank, all scales | Rank, pairwise |\n'
    lines = [header, '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n']
    for r in records:
        s, a = r['results'].get(EXPERIMENTS[0], {}), r['results'].get(EXPERIMENTS[1], {})
        vals = [s.get('traffic_reduction_pct'), s.get('traffic_MB'), s.get('adjacent_pair_accuracy'), s.get('mean_abs_rank_error'), s.get('p99_abs_rank_error'), a.get('deferred_update_savings_pct'), r.get('rank_honest_pool'), r.get('rank_all_pool'), r.get('rank_pairwise')]
        lines.append('| '+r['name']+' | '+r['status']+' | '+' | '.join('missing' if x is None else f'{x:.6f}' for x in vals)+' |\n')
    (AUDIT / 'results.md').write_text(''.join(lines))
    print(''.join(lines), flush=True)


if __name__ == '__main__':
    main()
