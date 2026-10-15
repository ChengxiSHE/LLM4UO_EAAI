"""Project evaluator-only outcomes for the already frozen V8 development set."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/text2opt_bench_20261003"
SPLIT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_v8_grouped_split_v1.json"
OUTPUT = ROOT / "data/next_development/text2opt_v8/evaluator.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text())
    if sha(SPLIT) != manifest["bindings"]["prepared_split_sha256"]:
        raise ValueError("v8_split_changed")
    split = json.loads(SPLIT.read_text())
    references = {}
    source_hashes = {}
    for row in split["development"]:
        path = SOURCE / row["source_file"]
        if sha(path) != row["source_file_sha256"]:
            raise ValueError("v8_development_source_changed:" + row["id"])
        source = json.loads(path.read_text())
        result = source.get("gurobi_result")
        if not isinstance(result, dict):
            raise ValueError("missing_development_result:" + row["id"])
        reference = {
            "solver_status": result.get("solver_status"),
            "theoretical_optimum": result.get("theoretical_optimum"),
        }
        if type(reference["solver_status"]) is not int or type(reference["theoretical_optimum"]) not in (int, float):
            raise ValueError("invalid_development_result:" + row["id"])
        references[row["id"]] = reference
        source_hashes[row["id"]] = row["source_file_sha256"]
    if len(references) != 70 or set(references) != {row["id"] for row in split["development"]}:
        raise ValueError("development_reference_set_mismatch")
    value = {
        "schema": "text2opt-v8-development-evaluator-v1",
        "role": "development_only_never_confirmation",
        "source_revision": split["source_revision"],
        "split_manifest_sha256": sha(MANIFEST),
        "gold_programs_executed": False,
        "projected_fields": ["solver_status", "theoretical_optimum"],
        "source_file_sha256": source_hashes,
        "references": references,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "references": len(references),
                      "sha256": sha(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
