#!/usr/bin/env python3
"""Execute the frozen mixed public bundle through the public-only router."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm4or.mixed_skill_execution import execute_mixed_record


BUNDLE = Path("experiments/mixed_skill_confirmation_bundle_20261014.json")
OUTPUT = Path("results/mixed_skill_confirmation_outputs_20261014.json")
BUNDLE_SHA256 = "944757ee0ef04111c3ff921e32f321385787c102a528bba6165c00addd4dafbb"
CODE_SHA256 = {
    "llm4or/mixed_skill_execution.py": "b9928572da49960db693c55ce4fe631462ce2660cd877b9d691016c3aabfae83",
    "llm4or/mixed_skill_router.py": "950c817a60f87a8fcdbb024bab84895b4b7e547ae772f285f00bbe0977e72a83",
    "llm4or/schema.py": "82a63e82f4cf72b99f4f58be2ff5ece44ad8b8ae8c08c0aa440d8615d6d9e428",
    "llm4or/or_debug_evolved_skill.py": "3eb6d961313b34fd57ad0d13309e716379e11b0d46dd254914de64fad85b5e93",
    "llm4or/or_debug_gurobi.py": "97691082bfe6ba48bdfdedf33f8df5abcbdb8baf44cd59c72d96f7752cb9cf8b",
    "llm4or/or_debug_iis_control.py": "7b911b667ee71272811ee5ee6980e13811703468d3f948b2ac8b16021581124e",
    "llm4or/or_debug_mps.py": "f598e37dce8d133c458258d5c87a30746bb7b66ffe25401e15b3b37b7be1ec9c",
    "llm4or/or_debug_mps_inspect.py": "389962c1aaa58fdd3b5c2aafe9ef910ae428fafd2084def1a3c6ab118cc42eaa",
    "llm4or/or_debug_public_runner.py": "60049e80ee3e2dd1c2d133cfa127461983de9a3321a49bd69f6acf41a80318be",
    "llm4or/tsp_constraint_skill.py": "2bb4712061c112c155678f00d301519edaaf40be978a893585f1e86f4a1256df",
    "llm4or/tsp_constraint_skill_scalable.py": "7130d57f2f6821720e5002c4ad6841ee6cd5df7b1aca0871338b4165eec19653",
    "llm4or/tsp_graph_exact.py": "4b1f68d16e89af67370669b6812c5b5a0ca380ee5068ac2244f093987364f4b1",
    "llm4or/tsp_public_graph.py": "46f7eb934b84ae72595c8813dfaf838bbec37d31e891bef733f44c7777ffd93e",
    "llm4or/tsp_scalable_exact.py": "8bcf804cb47430fb014bee4ad8695d7cdc42699fff8dff654b9c27287317b5bc",
    "llm4or/tsp_static_controller.py": "0f1368b13891473019de4a1829649ca80b3a54d6588c9a2900d889dbd9609d63",
    "llm4or/tsp_typed_graph.py": "1703c0e79251b3663ae1d368857626e9b5ca70f327e0478d6aa53a3c4708ba2b",
    "llm4or/gurobi_cli_solver.py": "59bc10e45901908c0782767dfc70fbf3bd248af6c671d0c62b396bdfd295e126",
    "llm4or/milp_schema.py": "0900e2e5d9e4669b5067209ead0d3ab221e6b78bbdd5f5ed120670f452703556",
    "llm4or/milp_solver.py": "2a30ce4668ab04ad823f9b93adfabc291f4e76ba0f80e9614d21540d20522858",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_code_pins(root: Path) -> dict[str, str]:
    """Verify every project module that contributes to mixed execution."""

    observed = {}
    for relative, expected in CODE_SHA256.items():
        value = _sha256(Path(root) / relative)
        if value != expected:
            raise ValueError(f"mixed method code SHA256 mismatch: {relative}")
        observed[relative] = value
    return observed


@contextmanager
def reserve_output(output: Path):
    """Exclusively reserve an immutable output name before dispatch."""

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    reservation = output.with_suffix(output.suffix + ".reservation")
    descriptor = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, b"mixed-skill-confirmation-v2\n")
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        yield reservation
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        reservation.unlink(missing_ok=True)


def publish_new(temporary: Path, output: Path) -> None:
    """Atomically publish without replacing any competing terminal file."""

    temporary = Path(temporary)
    output = Path(output)
    try:
        os.link(temporary, output)
    except FileExistsError:
        raise FileExistsError(f"terminal output appeared during execution: {output}")
    temporary.unlink()


def run_records(
    records: list[dict[str, Any]],
    *,
    model_root: Path,
    workspace_root: Path,
    execute: Callable[..., dict[str, Any]] = execute_mixed_record,
    max_workers: int = 5,
) -> list[dict[str, Any]]:
    """Execute each record once, preserving the frozen bundle order."""

    if not 1 <= max_workers <= 5:
        raise ValueError("mixed execution concurrency must be between one and five")
    outputs: list[dict[str, Any] | None] = [None] * len(records)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                execute,
                record,
                model_root=Path(model_root),
                workspace=Path(workspace_root) / f"{index:06d}",
            ): index
            for index, record in enumerate(records)
        }
        for completed, future in enumerate(as_completed(future_to_index), start=1):
            index = future_to_index[future]
            try:
                outputs[index] = future.result()
            except Exception as exc:
                record = records[index]
                outputs[index] = {
                    "record_id": record.get("record_id"),
                    "source": record.get("source"),
                    "route": None,
                    "status": "execution_failed",
                    "reason": type(exc).__name__,
                }
            if completed % 100 == 0 or completed == len(records):
                print(f"completed {completed}/{len(records)}", flush=True)
    if any(output is None for output in outputs):
        raise RuntimeError("mixed executor omitted a terminal record")
    return [output for output in outputs if output is not None]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if root != ROOT.resolve():
        raise ValueError("--root must equal the loaded script checkout")
    output = args.output or (root / OUTPUT)
    bundle_path = root / BUNDLE
    if _sha256(bundle_path) != BUNDLE_SHA256:
        raise ValueError("mixed public bundle SHA256 mismatch")
    verify_code_pins(root)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    records = bundle.get("records")
    if not isinstance(records, list) or len(records) != 2_985:
        raise ValueError("mixed public bundle denominator mismatch")

    with reserve_output(output):
        started = time.monotonic()
        model_root = root / "vendor/solver-in-the-loop/or_debug_bench"
        with tempfile.TemporaryDirectory(prefix="mixed-skill-confirmation-") as tmp:
            outputs = run_records(
                records,
                model_root=model_root,
                workspace_root=Path(tmp),
                max_workers=5,
            )
        result = {
            "schema": "llm4or.mixed_skill_confirmation_outputs.v1",
            "bundle_sha256": BUNDLE_SHA256,
            "code_sha256": dict(sorted(CODE_SHA256.items())),
            "execution": {
                "api_or_model_requests": 0,
                "concurrency": 5,
                "elapsed_seconds": time.monotonic() - started,
                "retries": 0,
                "status_counts": dict(sorted(Counter(row["status"] for row in outputs).items())),
            },
            "records": outputs,
        }
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        publish_new(temporary, output)
    print(json.dumps({"output": str(output), "records": len(outputs), "sha256": _sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
