"""Answer-blind custody for the fixed SOVER NLEquiv-150 source."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .atomic_publisher import publish_bundle
from .schema import canonical, digest


class NLEquivCustodyError(ValueError):
    pass


@dataclass(frozen=True)
class SourceIdentity:
    commit: str
    dataset_tree: str

    def __post_init__(self):
        for value in (self.commit, self.dataset_tree):
            if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
                raise NLEquivCustodyError("source_identity")


FORMULATION_KEYS = frozenset({
    "constraints", "keywords", "notes", "objective", "pair_id",
    "parameters", "parametrized_description", "variables",
})


def _raw(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise NLEquivCustodyError("source_file_unsafe")
    return path.read_bytes()


def _load(path: Path) -> tuple[bytes, Any]:
    raw = _raw(path)
    try:
        return raw, json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise NLEquivCustodyError("source_json") from exc


def _bytes(value: Any) -> bytes:
    return (canonical(value) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _index(records: Any, expected: int) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list) or len(records) != expected:
        raise NLEquivCustodyError("record_count")
    result = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != FORMULATION_KEYS:
            raise NLEquivCustodyError("formulation_schema")
        pair_id = row.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id or pair_id in result:
            raise NLEquivCustodyError("pair_identity")
        result[pair_id] = row
    return result


def build_custody(source_root: str | Path, identity: SourceIdentity) -> tuple[dict[str, bytes], dict[str, Any]]:
    root = Path(source_root).resolve() / "data" / "NLEquiv-150"
    required = {
        "labels.json", "metadata.json", "nlequiv150.jsonl",
        "positive/formulation_A.json", "positive/formulation_B.json",
        "positive/ground_truth_mappings.json", "positive/llm_extracted_mappings.json",
        "negative/formulation_A.json", "negative/formulation_B.json",
        "negative/ground_truth.json", "negative/ground_truth_candidate_mappings.json",
        "negative/llm_extracted_mappings.json",
    }
    file_hashes = {name: _sha(_raw(root / name)) for name in sorted(required)}
    _pos_a_raw, pos_a_value = _load(root / "positive/formulation_A.json")
    _pos_b_raw, pos_b_value = _load(root / "positive/formulation_B.json")
    _neg_a_raw, neg_a_value = _load(root / "negative/formulation_A.json")
    _neg_b_raw, neg_b_value = _load(root / "negative/formulation_B.json")
    _labels_raw, labels_value = _load(root / "labels.json")
    pos_a, pos_b = _index(pos_a_value, 100), _index(pos_b_value, 100)
    neg_a, neg_b = _index(neg_a_value, 50), _index(neg_b_value, 50)
    if set(pos_a) != set(pos_b) or set(neg_a) != set(neg_b) or set(pos_a) & set(neg_a):
        raise NLEquivCustodyError("pair_alignment")
    if not isinstance(labels_value, list) or len(labels_value) != 150:
        raise NLEquivCustodyError("label_count")
    labels = {}
    for row in labels_value:
        allowed = {"equivalent", "pair_id", "split"} | ({"mismatch_type"} if isinstance(row, dict) and row.get("equivalent") is False else set())
        if not isinstance(row, dict) or set(row) != allowed or type(row["equivalent"]) is not bool or row["pair_id"] in labels:
            raise NLEquivCustodyError("label_schema")
        labels[row["pair_id"]] = row
    if set(labels) != set(pos_a) | set(neg_a):
        raise NLEquivCustodyError("label_alignment")
    if any(not labels[pair_id]["equivalent"] or labels[pair_id]["split"] != "positive" for pair_id in pos_a):
        raise NLEquivCustodyError("positive_label_mismatch")
    if any(labels[pair_id]["equivalent"] or labels[pair_id]["split"] != "negative" for pair_id in neg_a):
        raise NLEquivCustodyError("negative_label_mismatch")

    entries: dict[str, bytes] = {}
    private_records = []
    public_descriptors = []
    for pair_id in sorted(labels):
        left = pos_a.get(pair_id, neg_a.get(pair_id))
        right = pos_b.get(pair_id, neg_b.get(pair_id))
        opaque = hashlib.sha256(f"{identity.commit}\0{pair_id}".encode()).hexdigest()
        inference = {
            "schema": "llm4or-nlequiv-inference-pair-v1",
            "opaque_id": opaque,
            "source_commit": identity.commit,
            "source_tree": identity.dataset_tree,
            "formulation_a": {key: value for key, value in left.items() if key != "pair_id"},
            "formulation_b": {key: value for key, value in right.items() if key != "pair_id"},
        }
        inference_raw = _bytes(inference)
        label = {"schema": "llm4or-nlequiv-evaluator-label-v1", "opaque_id": opaque, "equivalent": labels[pair_id]["equivalent"], "source_commit": identity.commit, "source_tree": identity.dataset_tree}
        label_raw = _bytes(label)
        metadata = {"schema": "llm4or-nlequiv-answer-free-metadata-v1", "opaque_id": opaque, "inference_sha256": _sha(inference_raw), "inference_bytes": len(inference_raw), "source_commit": identity.commit, "source_tree": identity.dataset_tree}
        metadata_raw = _bytes(metadata)
        entries[f"inference/{opaque}/pair.json"] = inference_raw
        entries[f"metadata/{opaque}.json"] = metadata_raw
        entries[f"evaluator/{opaque}/label.json"] = label_raw
        private_records.append({"opaque_id": opaque, "source_pair_id": pair_id, "split": labels[pair_id]["split"], "equivalent": labels[pair_id]["equivalent"], "inference_sha256": _sha(inference_raw), "label_sha256": _sha(label_raw)})
        public_descriptors.append({"opaque_id": opaque, "inference_sha256": _sha(inference_raw), "inference_bytes": len(inference_raw), "metadata_sha256": _sha(metadata_raw)})
    ledger = {"schema": "llm4or-nlequiv-private-custody-ledger-v1", "source": {"commit": identity.commit, "dataset_tree": identity.dataset_tree}, "records": private_records, "upstream_file_sha256": file_hashes}
    entries["private/ledger.json"] = _bytes(ledger)
    public_entries = {key: _sha(value) for key, value in entries.items() if key.startswith(("inference/", "metadata/"))}
    audit = {
        "schema": "llm4or-nlequiv-custody-audit-v1",
        "status": "passed",
        "source": {"commit": identity.commit, "dataset_tree": identity.dataset_tree},
        "counts": {"pairs": 150, "inference_records": 150, "metadata_records": 150, "evaluator_labels": 150},
        "public_descriptor_set_sha256": digest(public_descriptors),
        "inference_metadata_projection_sha256": digest(public_entries),
        "private_ledger_sha256": _sha(entries["private/ledger.json"]),
        "privacy": {"contains_labels": False, "contains_split_names": False, "contains_ground_truth_mappings": False, "contains_old_llm_mappings": False, "contains_non_equivalence_certificates": False, "contains_source_pair_ids": False},
        "license": {"identifier": "CC-BY-NC-4.0", "academic_noncommercial_use": True, "attribution_required": True},
        "execution": {"api_calls": 0, "model_calls": 0, "solver_calls": 0, "verifier_calls": 0, "credentials_read": False},
        "claim_boundary": "This audit establishes answer-blind source custody only; it reports no model accuracy.",
    }
    return dict(sorted(entries.items())), audit


def publish_custody(destination: str | Path, entries: Mapping[str, bytes]) -> None:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    publish_bundle(destination, entries)


__all__ = ["NLEquivCustodyError", "SourceIdentity", "build_custody", "publish_custody"]
