"""Answer-blind aggregation for the prospective RetailOpt-190 comparison."""

from __future__ import annotations

from collections import defaultdict
from math import comb
from typing import Any, Iterable, Mapping


ARMS = ("base_short", "knowledge_short")


class RetailEvaluationError(ValueError):
    pass


def one_sided_exact_mcnemar(corrections: int, regressions: int) -> float:
    """Exact Pr[X >= corrections], X~Binomial(discordant, .5)."""

    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (corrections, regressions)):
        raise RetailEvaluationError("paired_counts")
    discordant = corrections + regressions
    if discordant == 0:
        return 1.0
    return sum(comb(discordant, k) for k in range(corrections, discordant + 1)) / (2 ** discordant)


def aggregate_evaluation(
    observations: Iterable[Mapping[str, Any]],
    *,
    inference_completed: Mapping[str, int],
    expected_instances_per_arm: int = 190,
    expected_archetypes: int = 38,
) -> dict[str, Any]:
    """Aggregate private per-instance correctness into a body-free result."""

    rows = list(observations)
    by_arm: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    paired_instances: dict[str, dict[str, bool]] = defaultdict(dict)
    archetypes: dict[str, dict[str, list[bool]]] = {arm: defaultdict(list) for arm in ARMS}
    terminal_counts: dict[str, dict[str, int]] = {arm: defaultdict(int) for arm in ARMS}
    solver_status: dict[str, dict[str, int]] = {arm: defaultdict(int) for arm in ARMS}
    for row in rows:
        if set(row) != {"arm", "opaque_archetype_id", "opaque_instance_id", "terminal", "solver_status", "correct"}:
            raise RetailEvaluationError("observation_keys")
        arm = row["arm"]
        if arm not in ARMS or not isinstance(row["correct"], bool):
            raise RetailEvaluationError("observation_value")
        instance = row["opaque_instance_id"]
        if arm in paired_instances[instance]:
            raise RetailEvaluationError("duplicate_instance_arm")
        paired_instances[instance][arm] = row["correct"]
        by_arm[arm].append(row)
        archetypes[arm][row["opaque_archetype_id"]].append(row["correct"])
        terminal_counts[arm][row["terminal"]] += 1
        if row["solver_status"] is not None:
            solver_status[arm][row["solver_status"]] += 1
    if any(len(by_arm[arm]) != expected_instances_per_arm for arm in ARMS):
        raise RetailEvaluationError("instance_denominator")
    if len(paired_instances) != expected_instances_per_arm or any(set(value) != set(ARMS) for value in paired_instances.values()):
        raise RetailEvaluationError("instance_pairing")
    if any(len(archetypes[arm]) != expected_archetypes or any(len(v) != 5 for v in archetypes[arm].values()) for arm in ARMS):
        raise RetailEvaluationError("archetype_grid")

    instance_correct = {arm: sum(row["correct"] for row in by_arm[arm]) for arm in ARMS}
    fully_correct = {
        arm: {key: all(values) for key, values in archetypes[arm].items()}
        for arm in ARMS
    }
    archetype_correct = {arm: sum(fully_correct[arm].values()) for arm in ARMS}
    instance_corrections = sum(not pair["base_short"] and pair["knowledge_short"] for pair in paired_instances.values())
    instance_regressions = sum(pair["base_short"] and not pair["knowledge_short"] for pair in paired_instances.values())
    keys = set(fully_correct["base_short"])
    if keys != set(fully_correct["knowledge_short"]):
        raise RetailEvaluationError("archetype_pairing")
    corrections = sum(not fully_correct["base_short"][key] and fully_correct["knowledge_short"][key] for key in keys)
    regressions = sum(fully_correct["base_short"][key] and not fully_correct["knowledge_short"][key] for key in keys)
    p_value = one_sided_exact_mcnemar(corrections, regressions)
    completion_fraction = {arm: inference_completed.get(arm, 0) / expected_archetypes for arm in ARMS}
    accuracy = {arm: instance_correct[arm] / expected_instances_per_arm for arm in ARMS}
    ratio = float("inf") if regressions == 0 and corrections > 0 else (corrections / regressions if regressions else 0.0)
    checks = {
        "positive_instance_gain_at_least_0_05": accuracy["knowledge_short"] - accuracy["base_short"] >= 0.05,
        "archetype_corrections_at_least_6": corrections >= 6,
        "archetype_regressions_at_most_2": regressions <= 2,
        "correction_regression_ratio_at_least_2": ratio >= 2.0,
        "one_sided_exact_mcnemar_below_0_05": p_value < 0.05,
        "inference_completion_fraction_at_least_0_99": all(value >= 0.99 for value in completion_fraction.values()),
    }
    return {
        "instances": {
            arm: {"correct": instance_correct[arm], "total": expected_instances_per_arm, "accuracy": accuracy[arm]}
            for arm in ARMS
        },
        "archetypes": {
            arm: {"fully_correct": archetype_correct[arm], "total": expected_archetypes, "accuracy": archetype_correct[arm] / expected_archetypes}
            for arm in ARMS
        },
        "paired_instances": {"corrections": instance_corrections, "regressions": instance_regressions},
        "paired_archetypes": {"corrections": corrections, "regressions": regressions, "one_sided_exact_mcnemar_p": p_value},
        "inference_completed": {arm: {"cells": inference_completed.get(arm, 0), "fraction": completion_fraction[arm]} for arm in ARMS},
        "terminal_counts": {arm: dict(sorted(terminal_counts[arm].items())) for arm in ARMS},
        "solver_status_counts": {arm: dict(sorted(solver_status[arm].items())) for arm in ARMS},
        "confirmation_gate": {"passed": all(checks.values()), "checks": checks},
    }


__all__ = ["ARMS", "RetailEvaluationError", "aggregate_evaluation", "one_sided_exact_mcnemar"]
