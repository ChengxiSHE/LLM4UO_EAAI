"""Pinned public inputs and conservative type triage; no reference access."""
import hashlib
import json
from pathlib import Path
import re

from .benchmark_inputs import BASE_PROFILE, payload_sha256, validate_public_input
from .schema import Invalid

SLUGS = {"IndustryOR": "industryor", "MAMO ComplexLP": "mamo_complexlp", "OptMATH-Bench": "optmath",
         "ComplexOR": "complexor", "OptiBench": "optibench", "NL4Opt": "nl4opt"}
# Signals are intentionally not a semantic classifier. Absence is never LP proof.
RULES = {
    "nonlinear_signal": r"\b(?:non[- ]?linear|quadratic|bilinear|nonconvex|second[- ]order cone|square root|squared|logarithmic|exponential)\b|\*\*\s*2|\^\s*2",
    "explicit_milp": r"\bmixed[- ]integer(?: linear)?\b|\bMILP\b",
    "explicit_ip": r"\binteger (?:linear )?program(?:ming)?\b|\bILP\b",
    "explicit_lp": r"\blinear program(?:ming)?\b|\bLP (?:model|problem|formulation)\b",
    "binary_signal": r"\bbinary\b|\b(?:0[-–]1|zero[- ]one) variables?\b|\bexactly one\b|\bwhether (?:to|a|each)\b",
    "integer_signal": r"\bintegers?\b|\bindivisible\b|\bwhole (?:number|units?)\b|\bnon[- ]?fractional\b",
    "continuous_signal": r"\bcontinuous(?:ly)?\b|\bdivisible\b|\bfractional (?:amount|quantit|variable)",
    "logical_signal": r"\bfixed (?:cost|charge)\b|\beither\b|\bonly if\b|\bif .{0,100} then\b",
}


def checked_json(root, path, expected):
    raw = (Path(root) / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise Invalid("pinned artifact changed: " + str(path))
    return json.loads(raw)


def load_public_registry(root):
    root = Path(root)
    plan = json.loads((root / "experiments/benchmark_plan.json").read_text())
    audit = json.loads((root / "data/manifests/benchmark_input_audit.json").read_text())
    audits = {b["name"]: b for b in audit["benchmarks"]}
    records = []
    for b in plan["benchmarks"]:
        a = audits[b["name"]]
        if a["source"] != b["source"]:
            raise Invalid("source pin drift")
        revision = b.get("available_input_revision")
        if b["name"] == "ComplexOR":
            if not revision:
                raise Invalid("explicit ComplexOR revision required")
            manifest = checked_json(root, revision["manifest"], revision["manifest_sha256"])
            data = checked_json(root, revision["export"], revision["export_sha256"])
            unresolved = {r["problem_id"] for r in manifest["unresolved"]}
            expected = {r["id"]: r["after"] for r in manifest["input_hashes"]}
            version, export = revision["name"], revision["export"]
        else:
            data = json.loads((root / a["export"]).read_text())
            expected = {r["id"]: r["payload_sha256"] for r in a["problem_audit"]}
            unresolved = set(); version = "original_pinned_export"; export = a["export"]
        if data["profile"] != BASE_PROFILE or len(data["problems"]) != b["source_rows_before_split"]:
            raise Invalid("public export profile/count changed")
        seen = set()
        for i, value in enumerate(data["problems"]):
            p = validate_public_input(value)
            if p["id"] in seen or p["profile"] != BASE_PROFILE or expected.get(p["id"]) != payload_sha256(p):
                raise Invalid("public input identity/hash changed")
            seen.add(p["id"])
            public_issues = consistency_issues(p)
            records.append({"id": p["id"], "benchmark": b["name"], "source_index": i,
                            "source": b["source"], "input_revision": version, "input_export": export,
                            "input_sha256": payload_sha256(p), "public": p,
                            "public_consistency_issues": public_issues,
                            "input_status": "unresolved_input_semantics" if p["id"] in unresolved or public_issues else "ready"})
        if seen != set(expected):
            raise Invalid("export membership changed")
    if len({r["id"] for r in records}) != len(records):
        raise Invalid("cross-benchmark duplicate IDs")
    return records


def consistency_issues(p):
    issues = []
    if p['id'] == 'complexor_cut':
        for instance in p['instances']:
            d = instance['input']
            for j in range(d['NumPatterns']):
                used = sum(d['Widths'][i]*d['NumRollsWidthPattern'][i][j] for i in range(d['NumWidths']))
                if used > d['RollWidth']:
                    issues.append(dict(kind='pattern_exceeds_roll_width',instance=instance['id'],pattern_zero_based=j,
                                       used_width=used,roll_width=d['RollWidth'],source='public_parameter_arithmetic'))
    return issues


def triage(payload):
    p = validate_public_input(payload)
    fields = [("text", p["text"])] + [("parameters." + x["symbol"] + ".definition", x["definition"]) for x in p["parameters"]]
    evidence = []
    for rule, regex in RULES.items():
        for field, text in fields:
            for match in list(re.finditer(regex, text, re.I))[:4]:
                evidence.append({"signal": rule, "field": field, "start": match.start(), "end": match.end(), "quote": match.group()})
    signals = {e["signal"] for e in evidence}
    suggested = ("nonlinear_or_conflicting" if "nonlinear_signal" in signals else
                 "MILP_declared" if "explicit_milp" in signals else "IP_declared" if "explicit_ip" in signals else
                 "LP_declared_review_discreteness" if "explicit_lp" in signals else "not_determined_from_text_rules")
    return {"type_triage": suggested, "evidence": evidence, "certified_problem_type": None,
            "domain_signals": sorted(signals & {"binary_signal", "integer_signal", "continuous_signal", "logical_signal"}),
            "execution_support": "requires_formulation_and_numerical_range_validation",
            "review_required": True, "absence_of_signal_is_not_linearity_proof": True}
