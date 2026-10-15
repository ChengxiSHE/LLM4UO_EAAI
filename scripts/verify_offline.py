"""Reproducible offline verification with durable results and no paid requests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm4or.pipeline import write_json


def main():
    source_hash = hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "llm4or").glob("*.py")))).hexdigest()[:12]
    integration = ROOT / "results" / ("offline_s0_" + source_hash)
    commands = [
        ("unit_and_integration_tests", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("existing_math_mechanisms", ["scripts/check_mechanism.py"]),
        ("upstream_integrity_audit", ["scripts/audit_sources.py"]),
        ("development_reference_checks", ["scripts/prepare_pilot.py"]),
        ("next_development_and_family_audit", ["scripts/prepare_next_development.py"]),
        ("process_limited_integration", ["scripts/run_offline.py", "--output", str(integration)]),
        ("resume_same_requests", ["scripts/run_offline.py", "--output", str(integration)]),
        ("verified_protocol_and_s1_regression", ["scripts/check_post_pilot.py"]),
    ]
    report = {"kind": "offline_verification_not_benchmark", "actual_api_requests": 0,
              "source_hash": source_hash, "integration_directory": str(integration), "steps": []}
    for name, arguments in commands:
        started = time.monotonic()
        try:
            run = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True,
                                 text=True, timeout=120)
            output = run.stdout + run.stderr
            returncode = run.returncode
        except subprocess.TimeoutExpired:
            output, returncode = "Verification step timeout", -1
        log = ROOT / "results/verification_logs" / (name + ".txt")
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output)
        step = {"name": name, "returncode": returncode,
                "seconds": time.monotonic() - started, "log": str(log.relative_to(ROOT))}
        if name == "unit_and_integration_tests":
            match = re.search(r"Ran (\d+) tests", output)
            step["tests_run"] = int(match[1]) if match else None
        report["steps"].append(step)
        print(name + (": PASS" if returncode == 0 else ": FAILED"), flush=True)
        if returncode:
            break
    report["passed"] = len(report["steps"]) == len(commands) and all(s["returncode"] == 0 for s in report["steps"])
    if report["passed"]:
        summary = json.loads((integration / "summary.json").read_text())
        report["final_reserved_attempts"] = summary["requests"]["attempts_including_failures"]
        report["passed"] = report["final_reserved_attempts"] == 15
    write_json(ROOT / "results/offline_verification.json", report)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
