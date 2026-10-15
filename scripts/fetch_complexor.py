"""Save a pinned ComplexOR distribution as inert, read-only source files.

No archive paths are extracted, and no downloaded Python is imported/executed.
The 37-problem ORMind distribution is explicitly a derivative, not certified
byte-identical to the original Chain-of-Experts paper release.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = "XiaoAI1989/ORMind"
REVISION = "f5bc4ff3b5bcc2db7ea88ab0783f8d9a4078ac30"
DEST = Path("data/raw/complexor_20260831/XiaoAI1989__ORMind")
MANIFEST = ROOT / "data/manifests/complexor_sources.json"
MAX_ARCHIVE = 25_000_000
MAX_FILE = 1_000_000
PROTOCOL_FILES = {"README.md", "LICENSE", "utils/test_generated_code.py", "utils/experiment_runner.py"}
DATA_FILES = {"input_targets.json", "data.json", "code_example.py"}


def archive_bytes(cache=None):
    if cache:
        if Path(cache).stat().st_size > MAX_ARCHIVE:
            raise ValueError("archive size cap")
        return Path(cache).read_bytes()
    url = f"https://codeload.github.com/{REPO}/tar.gz/{REVISION}"
    with requests.get(url, stream=True, timeout=(10, 40)) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > MAX_ARCHIVE:
                raise ValueError("archive size cap")
        return bytes(data)


def selected_files(raw):
    prefix = f"ORMind-{REVISION}/"
    selected = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 100_000_000:
            raise ValueError("expanded archive cap")
        for member in members:
            if member.isdir() and member.name == prefix.rstrip("/"):
                continue
            if not member.name.startswith(prefix):
                raise ValueError("unexpected archive revision/root")
            path = member.name[len(prefix):]
            parts = PurePosixPath(path).parts
            wanted = path in PROTOCOL_FILES or (
                len(parts) == 4 and parts[:2] == ("dataset", "ComplexOR")
                and parts[3] in DATA_FILES)
            if not wanted:
                continue
            if not member.isfile() or member.size > MAX_FILE or ".." in parts or path in selected:
                raise ValueError("unsafe or duplicate source member")
            selected[path] = archive.extractfile(member).read()
    problems = sorted({p.split("/")[2] for p in selected if p.startswith("dataset/")})
    if len(problems) != 37:
        raise ValueError("pinned source problem count changed")
    for problem in problems:
        if any(f"dataset/ComplexOR/{problem}/{name}" not in selected for name in DATA_FILES):
            raise ValueError("missing problem component")
    if not {"README.md", "LICENSE", "utils/test_generated_code.py"} <= selected.keys():
        raise ValueError("missing source documentation")
    return selected, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached-archive", help="Optional already downloaded pinned archive")
    args = parser.parse_args()
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        for record in manifest["records"]:
            path = ROOT / record["local_path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError("source snapshot changed: " + record["local_path"])
        print(json.dumps({"status": "existing_snapshot_verified", "files": len(manifest["records"])}))
        return
    raw = archive_bytes(args.cached_archive)
    selected, problems = selected_files(raw)
    # Validate complete selection before writing anything.
    for path, contents in selected.items():
        destination = ROOT / DEST / path
        if destination.exists() and destination.read_bytes() != contents:
            raise FileExistsError("never replace a differing source snapshot")
    records = []
    for path, contents in sorted(selected.items()):
        destination = ROOT / DEST / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(contents)
            destination.chmod(0o444)
        name = PurePosixPath(path).name
        role = {"data.json": "mixed_inputs_and_evaluator_only_outputs",
                "input_targets.json": "mixed_problem_text_and_structured_annotations",
                "code_example.py": "scaffold_inert_never_executed"}.get(name, "provenance_or_protocol_only")
        records.append({"repo": REPO, "revision": REVISION, "upstream_path": path,
                        "url": f"https://raw.githubusercontent.com/{REPO}/{REVISION}/{path}",
                        "local_path": str(destination.relative_to(ROOT)), "bytes": len(contents),
                        "sha256": hashlib.sha256(contents).hexdigest(), "role": role,
                        "repository_license": "Apache-2.0",
                        "data_license_note": "Repository license does not establish upstream ComplexOR redistribution rights."})
    manifest = {"schema": "complexor-source-v1", "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "repo": REPO, "revision": REVISION, "source_root": str(DEST),
                "archive_url": f"https://codeload.github.com/{REPO}/tar.gz/{REVISION}",
                "archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_bytes": len(raw),
                "source_problem_count": len(problems), "problem_ids": problems, "records": records,
                "upstream_lineage": "ComplexOR / Chain-of-Experts; ORMind restructured distribution",
                "data_license_status": "upstream_dataset_rights_not_established_for_redistribution",
                "local_edits_to_source": [], "source_code_executed": False,
                "selection_basis": "User-required ComplexOR, all 37 supplied problems; no outcome-based filtering",
                "ignored_files": ["legacy input.json", "answer.json", "output.json", "code.py", "other repository code"],
                "notes": ["Stored data.json outputs remain evaluator-only; the public adapter projects input only.",
                          "No equivalence with another 37/21/18 release or paper scores is assumed."]}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": "source_pinned", "problems": len(problems), "files": len(records),
                      "selected_bytes": sum(r["bytes"] for r in records), "actual_model_api_calls": 0}))


if __name__ == "__main__":
    main()
