#!/usr/bin/env python3
"""Generate frozen scalable static and typed-skill confirmation candidates."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.schema import digest
from llm4or.tsp_constraint_skill_scalable import (
    _run_static_scalable,
    run_tsp_constraint_scalable_cascade,
)


PUBLIC_INPUT = ROOT / "results/private/tsp_constraint_confirmation_public_20261014.json"
PUBLIC_INPUT_SHA256 = "7c5635e8b78fa2f5d7647890bd8d6199c00e28a128c1c55a1b48f43af12d2fc8"
SPLIT_SHA256 = "3b42e10c6c63840ce0b42e968a55bf16b109656c798fb50febc5282b405b074c"
FRONTEND_SHA256 = "7130d57f2f6821720e5002c4ad6841ee6cd5df7b1aca0871338b4165eec19653"
BACKEND_SHA256 = "8bcf804cb47430fb014bee4ad8695d7cdc42699fff8dff654b9c27287317b5bc"
PRIVATE_OUTPUT = ROOT / "results/private/tsp_constraint_confirmation_candidates_20261014.json"
PUBLIC_OUTPUT = ROOT / "results/tsp_constraint_confirmation_candidates_20261014.json"
ROW_FIELDS = {"problem_id", "size", "question_sha256", "public_text"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _encoded(value) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _write_new(path: Path, value) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_encoded(value))


def _compact(candidate: dict) -> dict:
    out = {key: value for key, value in candidate.items() if key != "semantic_evidence"}
    if "semantic_evidence" in candidate:
        out["semantic_evidence_sha256"] = digest(candidate["semantic_evidence"])
    return out


def run_rows(rows: list[dict]) -> tuple[dict, dict]:
    if type(rows) is not list or not rows:
        raise ValueError("rows")
    seen = set()
    static_rows = []
    skill_rows = []
    static_routes = Counter()
    skill_routes = Counter()
    by_size = defaultdict(lambda: {"static_adopted": 0, "skill_adopted": 0, "records": 0})
    for row in rows:
        if type(row) is not dict or set(row) != ROW_FIELDS:
            raise ValueError("public_row_schema")
        if (
            type(row["problem_id"]) is not str
            or not row["problem_id"]
            or row["problem_id"] in seen
            or type(row["size"]) is not int
            or not 13 <= row["size"] <= 19
            or type(row["question_sha256"]) is not str
            or type(row["public_text"]) is not str
            or hashlib.sha256(row["public_text"].encode()).hexdigest()
            != row["question_sha256"]
        ):
            raise ValueError("public_row_schema")
        seen.add(row["problem_id"])
        static = _run_static_scalable(row["public_text"], row["size"])
        skill = run_tsp_constraint_scalable_cascade(row["public_text"], row["size"])
        if static.get("question_sha256") is None:
            static = dict(static)
            static["question_sha256"] = row["question_sha256"]
        if (
            static.get("question_sha256") != row["question_sha256"]
            or skill.get("question_sha256") != row["question_sha256"]
        ):
            raise ValueError("candidate_binding")
        base = {
            "problem_id": row["problem_id"],
            "size": row["size"],
            "question_sha256": row["question_sha256"],
        }
        static_rows.append({**base, "candidate": _compact(static)})
        skill_rows.append({**base, "candidate": _compact(skill)})
        static_routes[static["route"]] += 1
        skill_routes[skill["route"]] += 1
        by_size[row["size"]]["records"] += 1
        by_size[row["size"]]["static_adopted"] += int(static["adopted"])
        by_size[row["size"]]["skill_adopted"] += int(skill["adopted"])

    private = {"static_rows": static_rows, "skill_rows": skill_rows}
    public = {
        "schema": "tsp-constraint-confirmation-candidates-v1",
        "role": "answer_free_frozen_confirmation_candidates",
        "records": len(rows),
        "static_adopted": sum(row["candidate"]["adopted"] for row in static_rows),
        "static_abstained": sum(not row["candidate"]["adopted"] for row in static_rows),
        "skill_adopted": sum(row["candidate"]["adopted"] for row in skill_rows),
        "skill_abstained": sum(not row["candidate"]["adopted"] for row in skill_rows),
        "static_route_counts": dict(sorted(static_routes.items())),
        "skill_route_counts": dict(sorted(skill_routes.items())),
        "by_size_coverage": {str(size): values for size, values in sorted(by_size.items())},
        "static_rows_sha256": digest(static_rows),
        "skill_rows_sha256": digest(skill_rows),
        "private_output_sha256": digest(private),
        "model_requests": 0,
        "api_requests": 0,
        "reference_answer_accessed": False,
        "benchmark_accuracy_established": False,
    }
    return public, private


def load_and_run(root=ROOT) -> tuple[dict, dict]:
    root = Path(root).resolve()
    if (
        _sha(root / PUBLIC_INPUT.relative_to(ROOT)) != PUBLIC_INPUT_SHA256
        or _sha(root / "llm4or/tsp_constraint_skill_scalable.py") != FRONTEND_SHA256
        or _sha(root / "llm4or/tsp_scalable_exact.py") != BACKEND_SHA256
    ):
        raise ValueError("freeze_pin")
    source = json.loads((root / PUBLIC_INPUT.relative_to(ROOT)).read_text())
    if (
        source.get("schema") != "tsp-constraint-confirmation-public-v1"
        or source.get("split_sha256") != SPLIT_SHA256
        or source.get("method_frozen_before_public_export") is not True
        or type(source.get("rows")) is not list
        or len(source["rows"]) != 140
    ):
        raise ValueError("public_input_schema")
    public, private = run_rows(source["rows"])
    public.update(
        {
            "public_input_sha256": PUBLIC_INPUT_SHA256,
            "split_sha256": SPLIT_SHA256,
            "frontend_sha256": FRONTEND_SHA256,
            "backend_sha256": BACKEND_SHA256,
            "runner_sha256": _sha(Path(__file__)),
            "claim_guard": (
                "These are answer-free frozen confirmation candidates. No reference "
                "answer or constraint label was read; accuracy requires a separately "
                "pinned owner-custody evaluator."
            ),
        }
    )
    return public, private


def main() -> None:
    public, private = load_and_run(ROOT)
    _write_new(PRIVATE_OUTPUT, private)
    _write_new(PUBLIC_OUTPUT, public)
    print(
        json.dumps(
            {
                key: public[key]
                for key in (
                    "records",
                    "static_adopted",
                    "static_abstained",
                    "skill_adopted",
                    "skill_abstained",
                    "static_route_counts",
                    "skill_route_counts",
                    "model_requests",
                    "api_requests",
                    "reference_answer_accessed",
                    "benchmark_accuracy_established",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
