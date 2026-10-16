"""Validate a completed formal evaluation and emit a non-secret aggregate manifest."""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest


def file_sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def aggregate_method(rows):
    result = {}
    for method, cells in sorted(rows.items()):
        matched = sum(x['evaluation'].get('published_proxy_match') is True for x in cells)
        infrastructure = sum(not x['evaluation'].get('evaluation_eligible', True) for x in cells)
        eligible = len(cells) - infrastructure
        result[method] = {
            'planned': len(cells),
            'matched': matched,
            'matched_over_full_denominator': matched / len(cells),
            'infrastructure_unavailable': infrastructure,
            'matched_over_eligible': matched / eligible if eligible else None,
            'logical_requests': sum(x.get('logical_usage', {}).get('logical_requests', 0) for x in cells),
            'logical_tokens': sum(x.get('logical_usage', {}).get('logical_tokens', 0) for x in cells),
        }
    return result


def aggregate_pairs(rows):
    indexed = {(x['id'], x['method'], x['replicate'], x['token_cap']): x for x in rows}
    result = []
    for old, new in [('Base', 'SolverRepair'), ('Base', 'A'), ('Base', 'B'),
                     ('A', 'SimpleAB'), ('B', 'SimpleAB'), ('SimpleAB', 'Full')]:
        pairs = [(x, indexed[(x['id'], new, x['replicate'], x['token_cap'])])
                 for x in rows if x['method'] == old]
        pairs = [(a, b) for a, b in pairs if a['evaluation'].get('evaluation_eligible', True)
                 and b['evaluation'].get('evaluation_eligible', True)]
        plus = sum(a['evaluation'].get('published_proxy_match') is not True
                   and b['evaluation'].get('published_proxy_match') is True for a, b in pairs)
        minus = sum(a['evaluation'].get('published_proxy_match') is True
                    and b['evaluation'].get('published_proxy_match') is not True for a, b in pairs)
        result.append({'old': old, 'new': new, 'eligible_pairs': len(pairs),
                       'new_only_match': plus, 'old_only_match': minus,
                       'net_match_difference': (plus-minus)/len(pairs) if pairs else None,
                       'distinct_discordant_problems': len({a['id'] for a, b in pairs
                           if (a['evaluation'].get('published_proxy_match') is True) !=
                              (b['evaluation'].get('published_proxy_match') is True)})})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--evaluation', default='evaluation_v2.json')
    parser.add_argument('--output', default=str(ROOT/'results/formal_results_validation.json'))
    args = parser.parse_args()
    directory = Path(args.run_directory).resolve()
    evaluation_path = directory/args.evaluation
    plan = json.loads((ROOT/'experiments/full_run_plan.json').read_text())
    complete = json.loads((directory/'completed.json').read_text())
    inference = json.loads((directory/'inference_complete.json').read_text())
    evaluation = json.loads(evaluation_path.read_text())
    plan_hash = digest(plan)
    if {complete['plan_sha256'], inference['plan_sha256'], evaluation['plan_sha256']} != {plan_hash}:
        raise ValueError('plan_binding_mismatch')
    expected = {(pid, method, replicate, cap) for pid in plan['public_inputs']
                for method in plan['methods'] for replicate in plan['replicates']
                for cap in plan['trajectory_token_caps']}
    keys = [(x['id'], x['method'], x['replicate'], x['token_cap']) for x in evaluation['cells']]
    if len(keys) != len(expected) or len(set(keys)) != len(expected) or set(keys) != expected:
        raise ValueError('evaluation_matrix_mismatch')
    by_method = defaultdict(list)
    locked_by_method = defaultdict(list)
    for row in evaluation['cells']:
        by_method[row['method']].append(row)
        if row['role'] == 'locked_test':
            locked_by_method[row['method']].append(row)
    reasons = Counter(x['evaluation']['reason'] for x in evaluation['cells'])
    unavailable_by_benchmark = Counter(x['benchmark'] for x in evaluation['cells']
                                       if not x['evaluation'].get('evaluation_eligible', True))
    independent = [x['evaluation']['independent_model_audit'] for x in evaluation['cells']
                   if x['evaluation'].get('independent_model_audit')]
    identity = json.loads((directory/'evolution/identity.json').read_text())
    final_programs = json.loads((directory/'evolution/final_programs.json').read_text())
    gates = [json.loads(path.read_text()) for path in sorted((directory/'evolution').glob('*_gate.json'))]
    correction = None
    original_path = directory/'evaluation.json'
    if original_path.exists() and original_path != evaluation_path:
        original = json.loads(original_path.read_text())
        old = {(x['id'], x['method'], x['replicate'], x['token_cap']): x['evaluation'] for x in original['cells']}
        new = {(x['id'], x['method'], x['replicate'], x['token_cap']): x['evaluation'] for x in evaluation['cells']}
        old_pairs = {(x['cohort'], x['old'], x['new'], x['replicate'], x['token_cap']): x
                     for x in original['paired_comparisons']}
        new_pairs = {(x['cohort'], x['old'], x['new'], x['replicate'], x['token_cap']): x
                     for x in evaluation['paired_comparisons']}
        correction = {
            'original_evaluation_sha256': file_sha256(original_path),
            'changed_evaluation_objects': sum(old[key] != new[key] for key in old),
            'changed_eligibility_flags': sum(old[key].get('evaluation_eligible') != new[key].get('evaluation_eligible') for key in old),
            'changed_proxy_values': sum(old[key].get('published_proxy_match') != new[key].get('published_proxy_match') for key in old),
            'changed_paired_rows': sum(old_pairs[key] != new_pairs[key] for key in old_pairs),
            'paired_rows': len(old_pairs),
            'maximum_absolute_net_effect_change': max(abs(old_pairs[key]['net_match_difference']-
                                                          new_pairs[key]['net_match_difference']) for key in old_pairs),
        }
    manifest = {
        'schema': 'formal-results-validation-v1',
        'evaluation_version': evaluation.get('evaluation_version'),
        'plan_sha256': plan_hash,
        'artifacts': {
            'completed_sha256': file_sha256(directory/'completed.json'),
            'inference_complete_sha256': file_sha256(directory/'inference_complete.json'),
            'evaluation_sha256': file_sha256(evaluation_path),
        },
        'integrity': {
            'matrix_cells_expected': len(expected), 'matrix_cells_observed': len(keys),
            'unique_cell_keys': len(set(keys)), 'test_feedback_used_for_evolution': evaluation['test_feedback_used_for_evolution'],
            'ledger_matches_completed_usage': complete['usage'] == inference['usage'],
        },
        'usage': complete['usage'],
        'evaluation_reasons': dict(sorted(reasons.items())),
        'true_infrastructure_unavailable': sum(unavailable_by_benchmark.values()),
        'infrastructure_unavailable_by_benchmark': dict(sorted(unavailable_by_benchmark.items())),
        'full_source_by_method': aggregate_method(by_method),
        'locked_test_by_method': aggregate_method(locked_by_method),
        'locked_test_paired': aggregate_pairs([x for x in evaluation['cells'] if x['role'] == 'locked_test']),
        'independent_audit': {
            'cells': len(independent),
            'formulation_supported': sum(x.get('formulation_check') != 'unsupported' for x in independent),
            'objective_match_available': sum(x.get('objective_match_proxy') is not None for x in independent),
        },
        'evolution': {
            'streams': len(final_programs),
            'changed_streams': sum(identity['initial'][key] != value for key, value in final_programs.items()),
            'gates': len(gates),
            'gate_reasons': dict(sorted(Counter(x.get('reason') for x in gates).items())),
        },
        'evaluation_correction': correction,
        'claim_guard': evaluation['claim_guard'],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'output': str(output), 'cells': len(keys), 'true_infrastructure_unavailable': manifest['true_infrastructure_unavailable']}))


if __name__ == '__main__':
    main()
