#!/usr/bin/env python3
"""Credential-free preflight for the frozen AntChat transport environment."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import certifi

from llm4or import formal_provider
from llm4or import public_antchat_transport as transport


REQUIREMENTS = ROOT / "requirements-provider.txt"
TRANSPORT_SOURCE = ROOT / "llm4or/public_antchat_transport.py"
PROVIDER_SOURCE = ROOT / "llm4or/formal_provider.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def verify_environment(expected_ca_sha256: str | None = None) -> dict[str, Any]:
    expected_ca_sha256 = expected_ca_sha256 or transport.VERIFIED_CA_SHA256
    bundle = Path(certifi.where()).read_bytes()
    bundle_sha256 = hashlib.sha256(bundle).hexdigest()
    version = importlib.metadata.version("certifi")
    imports = _imports(TRANSPORT_SOURCE)
    local_modules = {path.stem for path in (ROOT / "llm4or").glob("*.py")}
    external_imports = [
        name
        for name in imports
        if name not in sys.stdlib_module_names
        and name not in local_modules
        and name not in {"llm4or"}
    ]
    checks = {
        "certifi_version_matches": version == "2026.7.22",
        "ca_sha256_matches": bundle_sha256 == expected_ca_sha256,
        "transport_frozen_ca_matches": bundle_sha256 == transport.VERIFIED_CA_SHA256,
        "base_url_consistent": formal_provider.BASE_URL == transport.BASE_URL,
        "model_consistent": formal_provider.MODEL == transport.MODEL,
        "max_concurrency_fixed": transport.MAX_CONCURRENCY == 5,
        "third_party_imports_exact": external_imports == ["certifi"],
        "openai_sdk_not_required": "openai" not in imports,
        "requests_not_required": "requests" not in imports,
    }
    tls_context_verified = False
    if checks["transport_frozen_ca_matches"]:
        context = transport.tls_context(transport.VERIFIED_CA_SHA256)
        tls_context_verified = bool(context.check_hostname and context.verify_mode)
    checks["tls_context_verified"] = tls_context_verified
    passed = all(checks.values())
    return {
        "schema": "llm4or-provider-environment-preflight-v1",
        "status": (
            "passed_provider_transport_preflight"
            if passed
            else "provider_transport_preflight_failed"
        ),
        "base_url": formal_provider.BASE_URL,
        "model": formal_provider.MODEL,
        "max_concurrency": transport.MAX_CONCURRENCY,
        "transport_version": transport.VERSION,
        "python": sys.version.split()[0],
        "dependencies": {"certifi": version},
        "requirements_file": "requirements-provider.txt",
        "requirements_file_sha256": _sha(REQUIREMENTS),
        "ca_bundle": {
            "bytes": len(bundle),
            "sha256": bundle_sha256,
            "expected_sha256": expected_ca_sha256,
        },
        "transport_imports": imports,
        "third_party_imports": external_imports,
        "source_sha256": {
            "llm4or/public_antchat_transport.py": _sha(TRANSPORT_SOURCE),
            "llm4or/formal_provider.py": _sha(PROVIDER_SOURCE),
        },
        "checks": checks,
        "boundary": (
            "This proves only the local frozen transport dependency, CA binding, endpoint/model "
            "identity and TLS-context construction. It does not read profile metadata or a key, "
            "contact the provider, prove account authorization, replay trajectories or validate "
            "future provider behavior."
        ),
        "execution": {
            "model_calls": 0,
            "api_calls": 0,
            "solver_calls": 0,
            "native_evaluator_calls": 0,
            "vm_calls": 0,
            "profile_metadata_read": False,
            "credentials_read": False,
            "request_or_response_bodies_read": False,
            "evaluator_only_answers_read": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    report = verify_environment()
    raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.audit_out:
        output = Path(args.audit_out)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if not args.check or report["status"] == "passed_provider_transport_preflight" else 1


if __name__ == "__main__":
    raise SystemExit(main())
