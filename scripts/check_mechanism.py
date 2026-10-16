"""Small trusted semantic-feedback fixtures, not LLM/benchmark performance.

All models and clauses below are hand-written synthetic fixtures. These checks
do not validate natural-language extraction, teacher reliability or evolution.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog


TOL = 1e-8
BOX_ROWS = [[-1, 0], [0, -1], [1, 0], [0, 1]]
BOX_RHS = [0, 0, 1, 1]


def maximize(c, rows, rhs):
    """Small, explicitly bounded fixtures; all bounds are included in rows."""
    return linprog(-np.asarray(c, dtype=float), A_ub=rows, b_ub=rhs,
                   bounds=[(None, None)] * len(c), method='highs')


def feasible(point, rows, rhs, integer_indices=()):
    x = np.asarray(point, dtype=float)
    return bool(np.all(np.asarray(rows) @ x <= np.asarray(rhs) + TOL)
                and all(abs(x[j] - round(x[j])) <= TOL for j in integer_indices))


def containment_probe(source_rows, source_rhs, target_rows, target_rhs):
    """Find a source-feasible point violating a target LP row.

    Uses numerical optima for bounded synthetic LPs, not exact certificates.
    Timeout/infeasibility/unboundedness never becomes an equivalence claim.
    """
    n = len(source_rows[0])
    for row, rhs in zip(target_rows, target_rhs):
        scale = max(float(np.max(np.abs(row))), abs(float(rhs)))
        if scale == 0:
            continue
        solved = maximize(row, source_rows, source_rhs)
        if not solved.success:
            return {'status': 'unknown', 'solver_status': int(solved.status)}
        violation = float(np.dot(row, solved.x) - rhs)
        if violation / scale > TOL:
            assert feasible(solved.x, source_rows, source_rhs)
            assert not feasible(solved.x, target_rows, target_rhs)
            return {'status': 'difference_witness', 'point': solved.x.tolist(),
                    'violated_row': list(row), 'rhs': float(rhs),
                    'raw_residual': violation, 'scaled_residual': violation/scale}
    return {'status': 'contained_within_numerical_tolerance', 'dimension': n}


def preference_reversal(first_objective, second_objective, rows, rhs):
    """Seek x,y feasible for both models with strictly opposing preferences.

    Callers supply their common feasible region and canonical maximization
    objectives. Failure to find a strict reversal does not establish equivalence.
    """
    first_objective = np.asarray(first_objective, dtype=float)
    second_objective = np.asarray(second_objective, dtype=float)
    n = len(first_objective)
    constraints = [list(row) + [0.] * n + [0.] for row in rows]
    constraints += [[0.] * n + list(row) + [0.] for row in rows]
    constraints += [list(-first_objective) + list(first_objective) + [1.],
                    list(second_objective) + list(-second_objective) + [1.]]
    result = linprog([0.] * (2*n) + [-1.], A_ub=constraints,
                     b_ub=list(rhs) + list(rhs) + [0., 0.],
                     bounds=[(None, None)] * (2*n) + [(0., None)], method='highs')
    if not result.success:
        return {'status': 'unknown', 'solver_status': int(result.status)}
    if result.x[-1] <= TOL:
        return {'status': 'no_strict_reversal_found_not_equivalence'}
    return {'status': 'preference_reversal',
            'decision_pair': [result.x[:n].tolist(), result.x[n:2*n].tolist()],
            'margin': float(result.x[-1])}


def main():
    correct_rows, correct_rhs = BOX_ROWS + [[1, 1]], BOX_RHS + [1]
    correct = maximize([1, 0], correct_rows, correct_rhs)
    omitted_constraint = maximize([1, 0], BOX_ROWS, BOX_RHS)
    assert correct.success and omitted_constraint.success
    assert abs(correct.fun - omitted_constraint.fun) < 1e-10
    witness = containment_probe(BOX_ROWS, BOX_RHS, correct_rows, correct_rhs)
    assert witness['status'] == 'difference_witness'

    # Same objective, excessive restriction: a reverse-direction probe is needed.
    restrictive_rows, restrictive_rhs = correct_rows + [[0, 1]], correct_rhs + [0]
    restrictive = maximize([1, 0], restrictive_rows, restrictive_rhs)
    assert restrictive.success and abs(restrictive.fun-correct.fun) < TOL
    overrestriction = containment_probe(correct_rows, correct_rhs,
                                        restrictive_rows, restrictive_rhs)
    assert overrestriction['status'] == 'difference_witness'

    # Equivalent scaling/redundancy must not be diagnosed as a semantic error.
    scaled_rows = [[7*v for v in row] for row in correct_rows] + [[1, 0]]
    scaled_rhs = [7*v for v in correct_rhs] + [1]
    equivalence = [containment_probe(correct_rows, correct_rhs, scaled_rows, scaled_rhs),
                   containment_probe(scaled_rows, scaled_rhs, correct_rows, correct_rhs)]
    assert all(p['status'] == 'contained_within_numerical_tolerance' for p in equivalence)

    # Canonical decision mapping handles a pure x/y permutation.
    source_point = np.asarray([0.2, 0.7])
    permuted_point = source_point[::-1]
    permuted_rows = [row[::-1] for row in correct_rows]
    assert feasible(source_point, correct_rows, correct_rhs)
    assert feasible(permuted_point, permuted_rows, correct_rhs)
    assert np.isclose(np.dot([1, 2], source_point), np.dot([2, 1], permuted_point))

    # Equal optimal scalar values do not imply the same objective preferences.
    objective_a, objective_b = np.array([2, 1]), np.array([1, 2])
    reversal = preference_reversal(objective_a, objective_b, correct_rows, correct_rhs)
    assert reversal['status'] == 'preference_reversal'
    first, second = map(np.asarray, reversal['decision_pair'])
    assert feasible(first, correct_rows, correct_rhs) and feasible(second, correct_rows, correct_rhs)
    objective_optima = [maximize(c, correct_rows, correct_rhs) for c in (objective_a, objective_b)]
    assert all(r.success for r in objective_optima)
    assert abs(objective_optima[0].fun-objective_optima[1].fun) < TOL
    assert objective_a @ (first-second) > 0 and objective_b @ (first-second) < 0

    # A common declared probe cannot distinguish two models if it misses the defect.
    zero = [0, 0]
    assert feasible(zero, BOX_ROWS, BOX_RHS) and feasible(zero, correct_rows, correct_rhs)
    assert feasible(zero, restrictive_rows, restrictive_rhs)
    assert not feasible([1, 1], correct_rows, correct_rhs)
    # Both candidates agree at (1,1), yet both violate the fixture's trusted clause.
    same_wrong_candidates = [feasible([1, 1], BOX_ROWS, BOX_RHS)] * 2
    assert all(same_wrong_candidates)

    # Integrality needs a domain probe; LP optimum comparisons are insufficient.
    fractional = [0.5, 0.5]
    assert feasible(fractional, correct_rows, correct_rhs)
    assert not feasible(fractional, correct_rows, correct_rhs, integer_indices=(0, 1))

    # Objective currency conversion alone is not a preference reversal.
    assert np.isclose((10*objective_a) @ first / 10, objective_a @ first)
    assert preference_reversal(objective_a, 10*objective_a, correct_rows, correct_rhs)['status'] == 'no_strict_reversal_found_not_equivalence'
    assert containment_probe(BOX_ROWS + [[1,0]], BOX_RHS + [-1],
                             correct_rows, correct_rhs)['status'] == 'unknown'
    result = {'kind': 'synthetic_mechanism_check_not_benchmark',
        'correct_objective': -float(correct.fun), 'incorrect_objective': -float(omitted_constraint.fun),
        'objective_match': True, 'violating_witness': witness['point'],
        'missing_constraint_residual': witness['raw_residual'], 'llm_requests': 0,
        'solver': 'scipy.optimize.linprog/HiGHS', 'passed': True,
        'cases': {
            'omission': witness,
            'overrestriction': overrestriction,
            'equivalent_scaled_redundant_constraints': equivalence,
            'variable_renaming': {'canonical_mapping_checked': True},
            'objective_preference_reversal': {
                'equal_optima': [-float(r.fun) for r in objective_optima],
                'decision_pair': [first.tolist(), second.tolist()],
                'a_scores': [float(objective_a @ p) for p in (first, second)],
                'b_scores': [float(objective_b @ p) for p in (first, second)],
                'solver_generated_margin': reversal['margin']},
            'finite_probe_blind_spot': {'agree_at_origin': True, 'models_equivalent': False},
            'shared_error': {'candidates_agree': True, 'trusted_clause_violated': True},
            'integrality': {'point': fractional, 'continuous_accepts_integer_rejects': True},
            'objective_unit_conversion': {'canonical_values_match': True}},
        'scope': 'trusted_handwritten_fixtures_only; no teacher, extraction, evolution, or accuracy evaluation'}
    output = Path(__file__).resolve().parents[1] / 'results/mechanism_check.json'
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
