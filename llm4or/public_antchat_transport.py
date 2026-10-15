"""Public, body-free AntChat transport identity and TLS construction."""
from __future__ import annotations

import hashlib
from pathlib import Path
import ssl

import certifi


VERSION = "antchat-public-transport-preflight-v1"
BASE_URL = "https://antchat.alipay.com/v1"
MODEL = "DeepSeek-V4-Flash"
MAX_CONCURRENCY = 5
VERIFIED_CA_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"


def tls_context(expected_ca_sha256: str) -> ssl.SSLContext:
    """Create a verified context only for the frozen CA-bundle identity."""

    if expected_ca_sha256 != VERIFIED_CA_SHA256:
        raise ValueError("unreviewed_ca")
    path = certifi.where()
    observed = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if observed != expected_ca_sha256:
        raise ValueError("ca_bundle_mismatch")
    return ssl.create_default_context(cafile=path)
