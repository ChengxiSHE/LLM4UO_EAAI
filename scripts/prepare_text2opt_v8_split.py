"""Freeze a grouped Text2Opt development/confirmation split before outcome use.

Only public snapshots and non-outcome metadata are read here.  Template
variants are excluded entirely, so no prose/capped variant of a retained
instance can cross the split.  Two records whose outcomes were inspected
during format auditing are forced into development and disclosed.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "data/prepared_benchmarks/text2opt_resource_allocation_v1.json"
TEMPLATE = ROOT / "data/prepared_benchmarks/text2opt_template_confirmation_v1.json"
OUTPUT = ROOT / "data/prepared_benchmarks/text2opt_v8_grouped_split_v1.json"
MANIFEST = ROOT / "data/manifests/text2opt_v8_grouped_split_v1.json"
MANUAL_EXPOSURES = {
    "text2opt_transportation_trans_001",
    "text2opt_jssp_jssp_001",
}


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def score(prefix, row):
    return sha_bytes((prefix + row["id"] + ":" + row["public_text_sha256"]).encode())


def resource_bin(row):
    size = row["non_outcome_metadata"]["num_vars"]
    if size <= 5:
        return "02_05"
    if size <= 10:
        return "06_10"
    if size <= 15:
        return "11_15"
    return "16_20"


def main():
    resource = json.loads(RESOURCE.read_text())
    template = json.loads(TEMPLATE.read_text())

    resource_groups = defaultdict(list)
    for row in resource["development"]:
        resource_groups[resource_bin(row)].append(row)
    resource_development = []
    for name, rows in sorted(resource_groups.items()):
        selected = sorted(rows, key=lambda row: score("v8-resource-development:", row))[:10]
        if len(selected) != 10:
            raise ValueError("insufficient_resource_stratum:" + name)
        for row in selected:
            resource_development.append({**row, "family": "resource_allocation", "stratum": name})

    template_groups = defaultdict(list)
    for row in template["confirmation"]:
        template_groups[row["family"]].append(row)
    template_development, template_confirmation = [], []
    for family, rows in sorted(template_groups.items()):
        forced = [row for row in rows if row["id"] in MANUAL_EXPOSURES]
        ranked = sorted(
            [row for row in rows if row["id"] not in MANUAL_EXPOSURES],
            key=lambda row: score("v8-template-development:", row),
        )
        selected_ids = {row["id"] for row in forced + ranked[: 5-len(forced)]}
        if len(selected_ids) != 5:
            raise ValueError("template_development_size:" + family)
        template_development.extend(row for row in rows if row["id"] in selected_ids)
        template_confirmation.extend(row for row in rows if row["id"] not in selected_ids)

    if not MANUAL_EXPOSURES <= {row["id"] for row in template_development}:
        raise ValueError("manual_exposure_not_in_development")
    development = sorted(resource_development + template_development, key=lambda row: row["id"])
    confirmation = sorted(
        [{**row, "family": "resource_allocation"} for row in resource["confirmation"]]
        + template_confirmation,
        key=lambda row: row["id"],
    )
    if len(development) != 70 or len(confirmation) != 401:
        raise ValueError("unexpected_split_size")
    dev_ids = {row["id"] for row in development}
    confirm_ids = {row["id"] for row in confirmation}
    if dev_ids & confirm_ids:
        raise ValueError("split_id_overlap")
    if MANUAL_EXPOSURES & confirm_ids:
        raise ValueError("exposed_record_in_confirmation")

    prepared = {
        "schema": "text2opt-v8-grouped-public-split-v1",
        "source_revision": resource["source_revision"],
        "model_visible_fields": ["id", "profile", "text", "parameters", "instances"],
        "development": development,
        "confirmation": confirmation,
    }
    OUTPUT.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")
    by_family = defaultdict(lambda: {"development": 0, "confirmation": 0})
    for role, rows in (("development", development), ("confirmation", confirmation)):
        for row in rows:
            by_family[row["family"]][role] += 1
    manifest = {
        "schema": "text2opt-v8-grouped-split-manifest-v1",
        "source_revision": resource["source_revision"],
        "selection_used_outcomes": False,
        "gold_programs_executed": False,
        "manual_outcome_exposures": sorted(MANUAL_EXPOSURES),
        "manual_exposure_disposition": "development_only_and_permanently_excluded_from_confirmation",
        "variant_policy": (
            "Only canonical small template files are used. small_prose and small_capped variants are excluded, "
            "so an instance and its rewrite cannot cross roles. Resource-allocation uses upstream train/eval roles."
        ),
        "selection_rule": (
            "Select 10 resource-allocation train records per non-outcome variable-count stratum by salted public hash; "
            "select five records per retained template family by salted public hash while forcing disclosed exposed "
            "records into development; all remaining previously capacity-compatible records stay confirmation-only."
        ),
        "counts": {
            "development": len(development),
            "confirmation": len(confirmation),
            "families": {name: value for name, value in sorted(by_family.items())},
        },
        "bindings": {
            "resource_public_snapshot_sha256": sha_file(RESOURCE),
            "template_public_snapshot_sha256": sha_file(TEMPLATE),
            "prepared_split_sha256": sha_file(OUTPUT),
            "development_public_sha256": sha_bytes(json.dumps(
                [[row["id"], row["public_text_sha256"]] for row in development],
                sort_keys=True, separators=(",", ":"),
            ).encode()),
            "confirmation_public_sha256": sha_bytes(json.dumps(
                [[row["id"], row["public_text_sha256"]] for row in confirmation],
                sort_keys=True, separators=(",", ":"),
            ).encode()),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
