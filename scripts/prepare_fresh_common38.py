#!/usr/bin/env python3
"""Publish the private common-38 packet and body-free readiness artifact."""

import json
from pathlib import Path

from llm4or.fresh_common38 import (
    build_private_bundle,
    build_public_manifest,
    publish_values,
)
from llm4or.schema import digest


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results/private/fresh_common38_packets_v1.json"
PUBLIC = ROOT / "experiments/fresh_common38_packet_readiness_20261015.json"


def main():
    bundle = build_private_bundle(ROOT)
    manifest = build_public_manifest(ROOT, bundle)
    publish_values(PRIVATE, PUBLIC, bundle, manifest)
    print(json.dumps({
        "state": "published",
        "records": manifest["cohort"]["records"],
        "private_bundle_sha256": digest(bundle),
        "public_readiness_sha256": digest(manifest),
        "static_compiled": manifest["static_compiler_readiness"]["compiled"],
        "static_failed": manifest["static_compiler_readiness"]["failed"],
        "api_calls": 0,
        "solver_calls": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
