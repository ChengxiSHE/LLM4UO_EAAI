"""Produce non-secret aggregate mechanism diagnostics from a completed formal run."""
from collections import Counter, defaultdict
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.schema import digest
from llm4or.formal_runtime import parse_model
from llm4or.milp_contracts import validate_output
from llm4or.milp_feedback import compile_record
from llm4or.milp_schema import loads


def file_sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def ordered(counter):
    return dict(sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))))


def model_hash(value):
    return digest(value) if isinstance(value, dict) and value.get('schema') != 'unsupported-v1' else None


def safe_contract_error(exc):
    value = str(exc)
    allowed = {'quote_provenance_mismatch', 'edit_lacks_replayed_target_evidence',
               'repair_requires_scope_and_protected_points', 'positive_example_not_teacher_feasible',
               'stale_teacher_input_or_models', 'nonrepair_edits', 'unaligned_teacher_interface',
               'unknown coefficient variable', 'invalid identifier', 'unsupported_contract',
               'teacher_unsupported', 'repair_unsupported'}
    if value in allowed or value.startswith('output_contract_violation:'):
        return value
    return type(exc).__name__


def response_contract_summary(directory):
    phase_map = {
        frozenset(): 'initial', frozenset({'initial', 'solve'}): 'baseline_repair',
        frozenset({'interface', 'objective_unit'}): 'teacher_model',
        frozenset({'initial', 'teacher', 'evidence', 'input_sha256', 'model_hashes', 'quote_spans'}): 'teacher_feedback',
        frozenset({'initial', 'teacher', 'teacher_packet'}): 'semantic_repair',
    }
    physical = Counter(); logical = Counter(); rebind_physical = Counter(); rebind_logical = Counter()
    with sqlite3.connect(directory/'requests.sqlite3') as database:
        database.row_factory = sqlite3.Row
        weights = dict(database.execute('SELECT key,count(*) FROM logical GROUP BY key'))
        attempts = list(database.execute("SELECT key,response FROM attempts WHERE status='complete'"))
    for attempt in attempts:
        path = directory/'request_payloads'/(attempt['key']+'.json')
        if not path.exists():
            continue
        saved = json.loads(path.read_text())
        payload = json.loads(saved['body']['messages'][1]['content'])
        phase = 'proposal' if payload.get('version') == 'workflow-v1' else phase_map.get(
            frozenset(payload.get('context', {})), 'unknown')
        outcome = 'contract_valid'
        try:
            text = json.loads(attempt['response'])['text']
            if phase == 'teacher_feedback':
                raw = validate_output(loads(text), teacher=True); context = payload['context']
                compile_record(raw, payload['problem'], context['initial'], context['teacher'], context['evidence'])
            elif phase in {'initial', 'baseline_repair', 'teacher_model', 'semantic_repair'}:
                value = parse_model(text)
                if phase == 'teacher_model' and value.get('schema') == 'unsupported-v1':
                    raise ValueError('teacher_unsupported')
                if phase in {'baseline_repair', 'semantic_repair'} and value.get('schema') == 'unsupported-v1':
                    raise ValueError('repair_unsupported')
            else:
                outcome = 'not_checked'
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            outcome = safe_contract_error(exc)
            if phase == 'teacher_feedback' and outcome == 'quote_provenance_mismatch':
                sources = {'text': payload['problem']['text']}
                for item in payload['problem']['parameters']:
                    sources['parameters.'+item['symbol']+'.definition'] = item['definition']
                hits = []
                for field, source in sources.items():
                    start = 0
                    while True:
                        index = source.find(raw['quote']['text'], start)
                        if index < 0:
                            break
                        hits.append((field, index)); start = index+1
                rebound = 'not_uniquely_rebindable'
                if len(hits) == 1:
                    fixed = deepcopy(raw); field, index = hits[0]
                    fixed['quote'].update(field=field, start=index, end=index+len(fixed['quote']['text']))
                    try:
                        packet = compile_record(fixed, payload['problem'], context['initial'], context['teacher'], context['evidence'])
                        rebound = 'compiled:'+packet['status']
                    except (ValueError, RuntimeError, KeyError, TypeError) as nested:
                        rebound = 'next_error:'+safe_contract_error(nested)
                rebind_physical[rebound] += 1
                rebind_logical[rebound] += weights.get(attempt['key'], 0)
        physical[phase+':'+outcome] += 1
        logical[phase+':'+outcome] += weights.get(attempt['key'], 0)
    return {'physical_unique_responses': ordered(physical), 'logical_uses': ordered(logical),
            'quote_rebinding_counterfactual': {'physical_unique_responses': ordered(rebind_physical),
                                               'logical_uses': ordered(rebind_logical)}}


def operation_summary(entries, grade_by_model):
    out = Counter()
    errors = Counter(); gates = Counter(); packets = Counter(); edits = Counter(); evidence = Counter(); transitions = Counter()
    for problem_id, entry in entries:
        out['scheduled'] += 1
        if not entry.get('triggered'):
            out['skipped'] += 1
            continue
        out['triggered'] += 1
        if entry.get('error'):
            out['errored'] += 1; errors[str(entry['error'])] += 1
        if entry.get('before_hash') != entry.get('after_hash'):
            out['model_changed'] += 1
        gate = entry.get('gate')
        if gate:
            if 'accepted' in gate:
                label = 'accepted' if gate['accepted'] else 'rejected'
            else:
                label = str(gate.get('status', gate.get('reason', 'unknown')))
            gates[label] += 1
            gates['reason:'+str(gate.get('reason', 'none'))] += 1
            if label in {'accepted', 'accepted_relative_to_evidence'}:
                out['gate_accepted'] += 1
        packet = entry.get('teacher_packet')
        if packet:
            out['teacher_packet_compiled'] += 1
            packets[str(packet.get('status', 'unknown'))] += 1
            packets['reason:'+str(packet.get('reason', 'none'))] += 1
            for edit in packet.get('edits', []): edits[str(edit.get('kind', 'unknown'))] += 1
        comparison = entry.get('evidence')
        if comparison:
            out['comparison_completed'] += 1
            if (comparison.get('left_to_right', {}).get('status') == 'witness' or
                    comparison.get('right_to_left', {}).get('status') == 'witness' or
                    comparison.get('preference', {}).get('status') == 'strict_reversal'):
                out['comparison_with_difference'] += 1
            evidence['overall:'+str(comparison.get('status'))] += 1
            evidence['left_to_right:'+str(comparison.get('left_to_right', {}).get('status'))] += 1
            evidence['right_to_left:'+str(comparison.get('right_to_left', {}).get('status'))] += 1
            evidence['preference:'+str(comparison.get('preference', {}).get('status'))] += 1
        if gate:
            out['gate_returned'] += 1
        if entry.get('error'):
            if entry.get('op') == 'semantic_review':
                stage = ('before_comparison' if not comparison else 'feedback_or_compile' if not packet else
                         'semantic_repair_or_gate' if not gate else 'after_gate')
            else:
                stage = 'repair_or_solve_before_gate' if not gate else 'after_gate'
            errors['inferred_stage:'+stage] += 1
        before = grade_by_model.get((problem_id, entry.get('before_hash')))
        after = grade_by_model.get((problem_id, entry.get('after_hash')))
        if before in {True, False} and after in {True, False}:
            transitions['known'] += 1
            transitions['correction' if after and not before else 'regression' if before and not after
                        else 'both_match' if before else 'neither_match'] += 1
    return {**dict(out), 'errors': ordered(errors), 'gates': ordered(gates),
            'teacher_packets': ordered(packets), 'edit_kinds': ordered(edits),
            'evidence': ordered(evidence), 'observable_proxy_transitions': ordered(transitions)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--evaluation', default='evaluation_v2.json')
    parser.add_argument('--output', default=str(ROOT/'results/formal_trajectory_analysis.json'))
    args = parser.parse_args()
    directory = Path(args.run_directory).resolve()
    evaluation_path = directory/args.evaluation
    evaluation = json.loads(evaluation_path.read_text())
    rows = evaluation['cells']
    records = {}
    for row in rows:
        path = Path(row['record_path'])
        record = json.loads(path.read_text())
        if digest(record) != row['record_sha256']:
            raise ValueError('record_hash_mismatch')
        records[(row['id'], row['method'], row['replicate'], row['token_cap'])] = record

    # A model hash has one deterministic published-label proxy outcome per problem.
    grade_sets = defaultdict(set)
    for row in rows:
        record = records[(row['id'], row['method'], row['replicate'], row['token_cap'])]
        value = row['evaluation'].get('published_proxy_match')
        h = model_hash(record.get('final_model'))
        if h and value in {True, False} and row['evaluation'].get('evaluation_eligible', True):
            grade_sets[(row['id'], h)].add(value)
    contradictions = {key: values for key, values in grade_sets.items() if len(values) != 1}
    if contradictions:
        raise ValueError('same_model_has_conflicting_proxy_grade')
    grade_by_model = {key: next(iter(values)) for key, values in grade_sets.items()}

    indexed_rows = {(x['id'], x['method'], x['replicate'], x['token_cap']): x for x in rows}
    by_method = {}
    for method in sorted({x['method'] for x in rows}):
        subset = [x for x in rows if x['method'] == method]
        statuses = Counter(); errors = Counter(); unsupported = Counter(); initial_solve = Counter(); final_solve = Counter()
        operations = defaultdict(list); model_changes = 0; initial_equals_base = Counter(); transitions = Counter()
        discordant_problems = set(); discordant_families = set(); discordant_benchmarks = Counter()
        for row in subset:
            key = (row['id'], method, row['replicate'], row['token_cap']); record = records[key]
            statuses[str(record.get('status'))] += 1
            for error in record.get('errors', []): errors[str(error.get('phase'))+':'+str(error.get('reason'))] += 1
            if record.get('unsupported_reason'): unsupported[str(record['unsupported_reason'])] += 1
            if record.get('initial_solve'): initial_solve[str(record['initial_solve'].get('status'))] += 1
            if record.get('final_solve'): final_solve[str(record['final_solve'].get('status'))] += 1
            ih, fh = model_hash(record.get('initial_model')), model_hash(record.get('final_model'))
            if ih and fh and ih != fh: model_changes += 1
            for entry in record.get('trace', []): operations[str(entry.get('op'))].append((row['id'], entry))
            base_key = (row['id'], 'Base', row['replicate'], row['token_cap'])
            base_record = records[base_key]; base_row = indexed_rows[base_key]
            bh = model_hash(base_record.get('final_model'))
            if ih and bh: initial_equals_base['equal' if ih == bh else 'different'] += 1
            if row['evaluation'].get('evaluation_eligible', True) and base_row['evaluation'].get('evaluation_eligible', True):
                old, new = base_row['evaluation'].get('published_proxy_match'), row['evaluation'].get('published_proxy_match')
                if old in {True, False} and new in {True, False}:
                    transitions['known'] += 1
                    transition = ('correction' if new and not old else 'regression' if old and not new
                                  else 'both_match' if old else 'neither_match')
                    transitions[transition] += 1
                    if transition in {'correction', 'regression'}:
                        discordant_problems.add(row['id']); discordant_families.add(row['family'])
                        discordant_benchmarks[row['benchmark']] += 1
        by_method[method] = {
            'planned': len(subset), 'record_status': ordered(statuses), 'errors': ordered(errors),
            'unsupported_reasons': ordered(unsupported), 'initial_solve_status': ordered(initial_solve),
            'final_solve_status': ordered(final_solve), 'records_with_changed_final_model': model_changes,
            'initial_model_vs_base': dict(initial_equals_base), 'final_proxy_transition_vs_base': ordered(transitions),
            'discordance_vs_base': {'problem_count': len(discordant_problems), 'family_count': len(discordant_families),
                                    'cells_by_benchmark': ordered(discordant_benchmarks)},
            'operations': {op: operation_summary(entries, grade_by_model) for op, entries in sorted(operations.items())},
        }

    method_cap = {}
    for method in sorted({x['method'] for x in rows}):
        for cap in sorted({x['token_cap'] for x in rows}):
            subset = [x for x in rows if x['method'] == method and x['token_cap'] == cap]
            op = Counter(); errors = Counter()
            for row in subset:
                record = records[(row['id'], method, row['replicate'], cap)]
                for entry in record.get('trace', []):
                    label = str(entry.get('op'))
                    op[label+':scheduled'] += 1
                    op[label+':triggered' if entry.get('triggered') else label+':skipped'] += 1
                    if entry.get('error'): op[label+':errored'] += 1
                    if entry.get('evidence'): op[label+':comparison_completed'] += 1
                    if entry.get('teacher_packet'): op[label+':teacher_packet_compiled'] += 1
                    gate = entry.get('gate', {})
                    if gate.get('accepted') is True or gate.get('status') == 'accepted_relative_to_evidence':
                        op[label+':accepted'] += 1
                for error in record.get('errors', []): errors[str(error.get('reason'))] += 1
            method_cap[f'{method}:{cap}'] = {
                'planned': len(subset),
                'matched': sum(x['evaluation'].get('published_proxy_match') is True for x in subset),
                'infrastructure_unavailable': sum(not x['evaluation'].get('evaluation_eligible', True) for x in subset),
                'operations': ordered(op), 'errors': ordered(errors),
            }

    exact_controls = {}
    for left, right in [('B', 'SolverRepair'), ('Full', 'SimpleAB')]:
        comparison = Counter()
        for row in (x for x in rows if x['method'] == left):
            key_left = (row['id'], left, row['replicate'], row['token_cap'])
            key_right = (row['id'], right, row['replicate'], row['token_cap'])
            lh = model_hash(records[key_left].get('final_model')); rh = model_hash(records[key_right].get('final_model'))
            if lh or rh: comparison['same_final_model' if lh == rh else 'different_final_model'] += 1
            if row['evaluation'] == indexed_rows[key_right]['evaluation']: comparison['same_evaluation'] += 1
            else: comparison['different_evaluation'] += 1
        exact_controls[f'{left}_vs_{right}'] = dict(comparison)

    base_reach = {}
    for benchmark in sorted({x['benchmark'] for x in rows}):
        subset = [x for x in rows if x['method'] == 'Base' and x['benchmark'] == benchmark]
        reached = sum(model_hash(records[(x['id'], 'Base', x['replicate'], x['token_cap'])].get('final_model')) is not None
                      for x in subset)
        base_reach[benchmark] = {'planned': len(subset), 'supported_initial_model': reached,
                                 'supported_initial_rate': reached/len(subset)}

    frozen_paths = sorted((directory/'evolution').glob('g*_frozen.json'))
    evolution = Counter(); patch_kinds = Counter(); rejected = Counter(); selection_deltas = []
    for path in frozen_paths:
        value = json.loads(path.read_text())
        evolution['streams_generations'] += 1
        evolution['valid_candidates'] += len(value['candidates'])
        evolution['proposal_rejections'] += len(value['rejected'])
        for candidate in value['candidates']: patch_kinds[str(candidate['patch'].get('kind'))] += 1
        for reason in value['rejected']: rejected[str(reason)] += 1
        incumbent = next(x for x in value['selection'] if x['label'] == 'inc')
        candidates = [x for x in value['selection'] if x['label'] != 'inc']
        if candidates:
            best = max(x['matches'] for x in candidates)
            selection_deltas.append(best-incumbent['matches'])
            evolution['candidate_beats_incumbent' if best > incumbent['matches'] else
                      'candidate_ties_incumbent' if best == incumbent['matches'] else 'candidate_loses_to_incumbent'] += 1
        if value['candidate_hash'] != digest(value['incumbent']): evolution['different_candidate_selected'] += 1
    gates = [json.loads(path.read_text()) for path in sorted((directory/'evolution').glob('*_gate.json'))]
    gate_reasons = Counter(str(x.get('reason')) for x in gates)
    gate_availability = Counter()
    for gate in gates:
        if gate.get('planned_pairs') is not None:
            gate_availability['planned_pairs'] += gate['planned_pairs']
            gate_availability['available_pairs'] += gate.get('available_pairs', 0)
    evolution.update(gates=len(gates), accepted_gates=sum(x.get('accept') is True for x in gates))

    output = {
        'schema': 'formal-trajectory-analysis-v1', 'plan_sha256': evaluation['plan_sha256'],
        'evaluation_version': evaluation.get('evaluation_version'), 'evaluation_sha256': file_sha256(evaluation_path),
        'scope': 'aggregate mechanism diagnostics only; no request/response text or evaluator-only answer content',
        'cells': len(rows), 'grade_by_model_entries': len(grade_by_model),
        'by_method': by_method, 'by_method_and_token_cap': method_cap,
        'base_initial_reach_by_benchmark': base_reach,
        'exact_control_comparisons': exact_controls,
        'response_contracts': response_contract_summary(directory),
        'evolution': {**dict(evolution), 'candidate_best_match_delta_vs_incumbent': ordered(Counter(selection_deltas)),
                      'patch_kinds': ordered(patch_kinds), 'proposal_rejection_types': ordered(rejected),
                      'gate_reasons': ordered(gate_reasons), 'selected_gate_availability': dict(gate_availability)},
        'interpretation_guard': ('Operation-level proxy transitions are observable only when both model hashes appear as '
                                 'eligible final models for the same problem. They are mechanism diagnostics, not semantic proof.'),
    }
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'output': str(path), 'cells': len(rows), 'methods': len(by_method)}))


if __name__ == '__main__':
    main()
