"""Pure scoring policies for the two published RetailOpt-190 contracts."""

from __future__ import annotations

import math
from typing import Any, Mapping


def relative_objective_error(observed: float, expected: float) -> float:
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in (observed, expected)):
        raise ValueError("objective_nonfinite")
    if expected == 0:
        return 0.0 if observed == 0 else math.inf
    return abs(observed - expected) / abs(expected)


def readme_strict_correct(record: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
    expected_status = record["reference_status"]
    observed_status = result["status"]
    status_ok = observed_status == expected_status or (
        expected_status == "OPTIMAL (TL)" and observed_status == "OPTIMAL"
    )
    tolerance = 0.01 if record["archetype"] in {"pack_size_integer", "fixed_order_cost"} else 0.0001
    return status_ok and relative_objective_error(result["objective"], record["reference_objective"]) <= tolerance


def reloop_code_correct(record: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
    """Match the official ReLoop code's objective-error classification."""

    return relative_objective_error(result["objective"], record["reference_objective"]) < 0.01


__all__ = ["readme_strict_correct", "relative_objective_error", "reloop_code_correct"]
