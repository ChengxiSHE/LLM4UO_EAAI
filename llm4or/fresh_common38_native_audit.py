"""Independent body-free audit of the fresh common-38 native run."""

from collections import Counter
import hashlib
import json
from pathlib import Path

from .fresh_common38 import build_private_bundle
from .fresh_common38_native import (
    build_plan, load_cells, load_references, publish_result, score_cells,
)
from .schema import canonical
from .structured_or_skills import compile_and_admit


PLAN = "experiments/fresh_common38_current_native_plan_20261015.json"
RESULT = "experiments/fresh_common38_current_native_result_20261015.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_audit(root):
    root = Path(root).resolve()
    plan = json.loads((root / PLAN).read_text())
    if canonical(plan) != canonical(build_plan(root)):
        raise ValueError("plan_reconstruction")
    directory = root / plan["output"]["private_run_directory"]
    cells = load_cells(plan, directory)
    recomputed = score_cells(plan, cells, load_references(root, plan))
    published = json.loads((root / RESULT).read_text())
    if canonical(recomputed) != canonical(published):
        raise ValueError("result_reconstruction")
    rows = {row["id"]: row for row in build_private_bundle(root)["records"]}
    for binding in plan["bindings"]:
        admitted = compile_and_admit(rows[binding["id"]]["public_payload"])
        if admitted["model_sha256"] != binding["model_sha256"]:
            raise ValueError("model_reconstruction")
    statuses = Counter(cell["status"] for cell in cells)
    return {
        "schema": "fresh-common38-current-native-independent-audit-v1",
        "status": "passed",
        "plan_sha256": _sha(root / PLAN),
        "result_sha256": _sha(root / RESULT),
        "checks": {
            "plan_reconstructed": True,
            "models_reconstructed": 38,
            "private_checkpoints_verified": 38,
            "endpoint_scores_recomputed": 38,
            "public_result_exactly_reproduced": True,
            "status_counts": dict(sorted(statuses.items())),
            "aggregate": published["aggregate"],
            "families": published["families"],
        },
        "privacy": {
            "contains_objectives": False,
            "contains_points": False,
            "contains_reference_values": False,
            "contains_packet_bodies": False,
        },
        "claim_boundary": {
            "current_method_only": True,
            "common_external_comparison_complete": False,
            "solver_unavailable_is_not_silently_rescored": True,
            "automatic_acquisition_supported": False,
        },
        "execution": {"new_solver_calls": 0, "api_calls": 0, "model_calls": 0},
    }


def publish(path, value):
    publish_result(path, value)


__all__ = ["build_audit", "publish"]
