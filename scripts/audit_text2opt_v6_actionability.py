"""Audit V6's necessary public-text triggers without reading any outcomes.

This script deliberately reads only the two prepared public snapshots.  A
public trigger is necessary, but not sufficient: the generated Base model
must still expose a uniquely alignable variable or row before V6 can edit it.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    ROOT / "data/prepared_benchmarks/text2opt_resource_allocation_v1.json",
    ROOT / "data/prepared_benchmarks/text2opt_template_confirmation_v1.json",
)
OUTPUT = ROOT / "results/text2opt_v6_confirmation_actionability_audit.json"
V1_COUNT_NOUNS = {"pill", "container", "chair", "order", "car", "vehicle", "worker", "machine"}
V2_COUNT_NOUNS = {"bag", "bottle", "can", "day", "experiment", "package", "process", "ream", "taco"}
QUESTION = re.compile(r"\bhow many\s+([^?]+)\?", re.I)
RATIO = re.compile(
    r"(?:minimum|at least)\s+(?:of\s+)?\d+(?:\.\d+)?%\s+of\s+"
    r"[^.]{1,120}?\s+(?:in|into|on)\s+[^.,]{1,120}?(?=\s+and\s+|[.,]|$)", re.I,
)
FLOW = re.compile(
    r"At location\s+\d+,\s+there are currently\s+\d+(?:\.\d+)?\s+cars present,\s+"
    r"but\s+\d+(?:\.\d+)?\s+cars are needed\.? ?", re.I,
)


def tokens(value):
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def count_nouns(values, vocabulary):
    found = set()
    for value in values:
        if value.endswith("es") and value[:-2] in vocabulary:
            value = value[:-2]
        elif value.endswith("s") and value[:-1] in vocabulary:
            value = value[:-1]
        if value in vocabulary:
            found.add(value)
    return found


def rows():
    resource = json.loads(INPUTS[0].read_text())
    for row in resource["confirmation"]:
        yield "resource_allocation", row["id"], row["public"]["text"]
    template = json.loads(INPUTS[1].read_text())
    for row in template["confirmation"]:
        yield row["family"], row["id"], row["public"]["text"]


def main():
    overall = Counter()
    by_category = defaultdict(Counter)
    identifiers = []
    for category, problem_id, text in rows():
        questions = QUESTION.findall(text)
        question_tokens = set().union(*(tokens(value) for value in questions)) if questions else set()
        flags = {
            "v1_count_public_trigger": bool(count_nouns(question_tokens, V1_COUNT_NOUNS)),
            "v2_count_public_trigger": bool(count_nouns(question_tokens, V2_COUNT_NOUNS)),
            "ratio_public_trigger": bool(RATIO.search(text)),
            "flow_public_trigger": len(FLOW.findall(text)) >= 2,
        }
        flags["any_v6_public_trigger"] = any(flags.values())
        overall["records"] += 1
        by_category[category]["records"] += 1
        for name, value in flags.items():
            overall[name] += int(value)
            by_category[category][name] += int(value)
        if flags["any_v6_public_trigger"]:
            identifiers.append(problem_id)
    result = {
        "schema": "text2opt-v6-public-actionability-audit-v1",
        "inputs": [str(path.relative_to(ROOT)) for path in INPUTS],
        "outcomes_read": False,
        "api_requests": 0,
        "interpretation": (
            "A public trigger is necessary but not sufficient for a V6 edit because Base must also expose "
            "a uniquely alignable interface. With zero public triggers, V6 is provably identical to Base."
        ),
        "overall": dict(overall),
        "by_category": {name: dict(value) for name, value in sorted(by_category.items())},
        "triggered_problem_ids": identifiers,
        "decision": "retire_before_authorization" if not identifiers else "continue_preflight",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
