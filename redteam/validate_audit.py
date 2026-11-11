"""Lightweight consistency checks on saved evidence; performs no experiments."""
from pathlib import Path
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'redteam'
summary = json.loads((AUDIT / 'summary.json').read_text())
records = {r['name']: r for r in summary['records']}
suite = json.loads((AUDIT / 'suite_status.json').read_text())
assert len(suite['cases']) == 20
assert not suite['harness_failures']
experiments = ['synthetic_temporal_sorting', 'deferred_depth_update_ablation']
for name in suite['cases']:
    info = json.loads((AUDIT / name / 'run_status.json').read_text())
    assert info['test_command'] == 'bash scripts/evaluate_test.sh'
    assert info['test_arguments'] == []
    assert info['evaluator_mutated'] is False
    assert (AUDIT / name / 'run.sh').exists()
    if info['test']['returncode'] == 0:
        payload = json.loads((AUDIT / name / 'scores_test.json').read_text())
        assert list(payload['experiments']) == experiments
    else:
        assert not (AUDIT / name / 'scores_test.json').exists()
        assert info['test_error_tail']
for filename, target in [('neo_sort.py', 'method/neo_sort.py'), ('full_sort.py', 'baseline/full_sort.py')]:
    assert (AUDIT / 'source' / filename).read_bytes() == (ROOT / target).read_bytes()
reference = records['reference_seed101']['results']
original_scores = json.loads((ROOT / 'scoring/scores_test.json').read_text())['experiments']
for experiment in experiments:
    for metric, value in reference[experiment].items():
        assert math.isclose(value, original_scores[experiment]['results']['neo_reuse_update'][metric], abs_tol=1e-10)
        for seed in [102, 103]:
            assert value == records[f'reference_seed{seed}']['results'][experiment][metric]
assert all(value == 0 for metrics in summary['seed_metric_ranges'].values() for value in metrics.values())
weak = records['weaker_no_partial_sort']
skip = records['shortcut_skip_bad_experiment']
assert experiments[0] not in skip['results']
for metric, value in weak['results'][experiments[1]].items():
    assert math.isclose(value, skip['results'][experiments[1]][metric], abs_tol=1e-10)
assert weak['rank_honest_pool'] < 0 < skip['rank_honest_pool']
assert records['better_current_depth_fix']['rank_honest_pool'] > 0
assert records['better_current_depth_fix']['rank_all_pool'] < 0 < weak['rank_all_pool']
dominating = ['shortcut_copy_sorted_input', 'shortcut_zero_traffic', 'shortcut_negative_traffic',
              'shortcut_baseline_inflate', 'shortcut_ablation_inflate', 'shortcut_omit_scenes',
              'shortcut_workload_shrink']
assert all(records[name]['pareto_dominates_reference'] for name in dominating)
assert records['shortcut_empty_scenes']['rank_pairwise'] > 0
for link in re.findall(r'\]\((redteam[^)]*)\)', (ROOT / 'REDTEAM.md').read_text()):
    assert (ROOT / link).exists(), link
print('PASS: 20 runs, original reference match, three identical seeds, seven Pareto shortcuts, and ranked experiment omission verified.')
