"""Prepare a narrow LP development pilot; never load test records or execute upstream code.

Numeric references below were transcribed from problem text, not obtained from LLM
calls. They are provisional assistant-reviewed references, not expert-certified gold.
"""
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm4or.pipeline import write_json
from llm4or.schema import digest, model, public_problem
from llm4or.solver import execute

# line, business variables, unit, objective, inequalities, expected objective.
# <= rows unless otherwise stated. No artificial upper bounds are introduced.
SPECS = [
    (6, ["2-piece suits", "3-piece suits"], "suit", [600, 800],
     [([1, 2], "le", 150), ([4, 5], "le", 300), ([1, 0], "ge", 40)], None),
    (7, ["Standard grade alloy", "Plus grade alloy", "Premium grade alloy"], "ton", [1500, 2500, 5500],
     [([3, 5, 6], "le", 150), ([1, 2, 3], "le", 35)], None),
    (11, ["Aleph 3 monitors", "Gilgamesh Supreme monitors"], "monitor", [1500, 2500],
     [([2, 2.5], "le", 5000), ([0.5, 0.5], "le", 2500)], None),
    (12, ["rice", "corn"], "kilogram", [20, 25],
     [([2, 1], "le", 100), ([3, 5], "le", 200), ([4, 1], "le", 75)], None),
    (14, ["strawberries", "watermelons"], "acre", [200, 500],
     [([1, 1], "le", 120), ([0.5, 0.2], "le", 150), ([1, 2], "le", 100)], None),
    (18, ["lemonade", "brownies"], "pitcher_or_batch", [20, 15],
     [([0.5, 1], "le", 10), ([0.2, 0.5], "le", 8)], None),
    (21, ["ham", "bacon"], "kilogram", [20, 12],
     [([15, 8], "le", 2000), ([1, 0], "le", 200), ([0, 1], "le", 220)], None),
    (34, ["mixture A", "mixture B"], "mixture_unit", [2, 4],
     [([3, 4], "le", 200), ([5, 7], "le", 300), ([2, 1], "le", 60)], None),
    (37, ["land served by large logging trucks", "land served by small logging trucks"], "acre", [7, 3],
     [([1, 1], "le", 450), ([12, 7], "le", 3200), ([25, 12], "le", 5200)], None),
    (51, ["chocolate powder", "vanilla powder"], "scoop", [20, 18],
     [([2, -1], "le", 0), ([1, 0], "ge", 2), ([4, 7], "le", 500)], None),
]


def enumerate_vertices(m):
    """Separate tiny-LP optimum check via active sets, without scipy/HiGHS."""
    import numpy as np
    ids = [v["id"] for v in m["variables"]]
    rows, bounds = [], []
    for r in m["constraints"]:
        a = [r["coefficients"][v] for v in ids]
        sign = 1 if r["sense"] == "le" else -1
        rows.append([sign * x for x in a]); bounds.append(sign * r["rhs"])
    for i in range(len(ids)):
        a = [0] * len(ids); a[i] = -1
        rows.append(a); bounds.append(0)
    a, b = np.array(rows), np.array(bounds)
    c = np.array([m["objective"]["coefficients"][v] for v in ids])
    values = []
    for inds in itertools.combinations(range(len(rows)), len(ids)):
        try:
            x = np.linalg.solve(a[list(inds)], b[list(inds)])
        except np.linalg.LinAlgError:
            continue
        if np.all(a @ x <= b + 1e-7):
            values.append(float(c @ x))
    if not values:
        raise ValueError("no feasible vertex")
    return max(values)


def main():
    manifest = json.loads((ROOT / "data/manifests/source_manifest.json").read_text())
    record = next(r for r in manifest["records"] if r["repo"] == "nl4opt/nl4opt-competition" and r["upstream_path"] == "generation_data/dev.jsonl")
    raw = (ROOT / record["local_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record["sha256"]
    data = [next(iter(json.loads(line).items())) for line in raw.splitlines() if line.strip()]
    entries = []
    public = []
    for line, meanings, unit, coefficients, rows, _ in SPECS:
        source_id, upstream = data[line - 1]
        pid = "dev_" + str(line).zfill(3)
        ids = ["v" + str(i+1) for i in range(len(meanings))]
        variables = [{"id": v, "meaning": meaning, "unit": unit, "domain": "continuous", "lower": 0, "upper": None}
                     for v, meaning in zip(ids, meanings)]
        if line == 18:
            variables[0]["unit"], variables[1]["unit"] = "pitcher", "batch"
        objective_unit = "eruption_unit" if line == 34 else "wood_unit" if line == 37 else "gram_protein" if line == 51 else "USD"
        ref = model({"schema": "lp-v1", "variables": variables,
                     "objective": {"coefficients": dict(zip(ids, coefficients)), "sense": "max", "unit": objective_unit, "offset": 0},
                     "constraints": [{"id": "r" + str(i+1), "coefficients": dict(zip(ids, a)), "sense": sense, "rhs": rhs}
                                     for i, (a, sense, rhs) in enumerate(rows)]})
        problem = public_problem(pid, upstream)
        result = execute({"op": "solve", "model": ref})
        independent = enumerate_vertices(ref)
        assert result["status"] == "optimal", (pid, result)
        assert abs(result["objective"] - independent) <= 1e-6 * max(1, abs(independent)), pid
        self_check = execute({"op": "compare", "left": ref, "right": ref})
        assert self_check.get("left_to_right", {}).get("status") == "contained_within_tolerance", (pid, self_check)
        # Most selected questions share a resource-allocation template. This is
        # intentionally a feasibility set, NOT ten independent statistical families.
        family = "bounded_ratio_mix" if line == 51 else "bounded_resource_allocation"
        audit = {"source_id": source_id, "source_line": line, "source_sha256": record["sha256"],
                 "reference_hash": digest(ref), "review": "assistant_text_transcription_provisional",
                 "reference": ref, "solver": result, "vertex_enumeration_objective": independent,
                 "assumptions": ["Nonnegative decisions", "Continuous LP quantities; explicit LP formulation for count-unit questions 6/11/18"],
                 "upstream_annotations": {"obj_declaration": upstream["obj_declaration"], "const_declarations": upstream["const_declarations"]},
                 "formal_equivalence_to_upstream_annotations": "not_claimed",
                 "note": "These annotations are evaluator-only. Neither these nor reference variables are included in public JSONL."}
        if line == 51:
            audit["assumptions"].append("Quantity is scoops of powder, continuously divisible; twice as many means vanilla>=2*chocolate.")
        write_json(ROOT / "data/pilot/evaluator" / (pid + ".json"), audit)
        public.append(problem)
        entries.append({"id": pid, "source_id": source_id, "source_line": line,
                        "public_hash": digest(problem), "family_provisional": family,
                        "reference_checked": "HiGHS_and_vertex_enumeration", "exclude_from_final_test": True})
    dest = ROOT / "data/pilot/public/problems.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in public))
    original_random = [i + 1 for i in random.Random(20260830).sample(range(len(data)), 10)]
    write_json(ROOT / "data/pilot/manifest.json", {
        "status": "provisional_development_feasibility_set_not_locked_benchmark",
        "source": record, "selection": "manual_bounded_continuous_LP_eligibility_before_any_model_outcomes",
        "superseded_random_candidate_lines": original_random,
        "superseded_reason": "Original random draw includes unbounded domains, discrete decisions and ambiguous/error annotations; no performance-based selection.",
        "entries": entries, "provisional_family_count": 2,
        "must_exclude_all_99_development_questions_from_final_test": True,
        "cross_source_family_dedup_complete": False,
        "limitations": ["Mostly packing LPs, not representative of all LLM4OR.",
                        "Assistant-reviewed references require independent semantic review before a formal benchmark claim.",
                        "Same text-derived variable meanings must be mapped by a separate evaluator after inference; no reference variables in prompts."]})
    print("Prepared 10 public-only development cases and separate reference audits; both numerical checks agree. Formal split remains unlocked.")


if __name__ == "__main__":
    main()
