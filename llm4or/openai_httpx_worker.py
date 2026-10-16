"""One-attempt OpenAI/httpx transport used by an external pinned interpreter.

The durable formal gateway owns retries and accounting.  This worker performs
exactly one non-streaming SDK call with SDK retries and environment proxies
disabled.  Exception messages and credentials never enter its result.
"""

from __future__ import annotations

from typing import Any, Callable

from .formal_provider import BASE_URL, MODEL, load_credential
from .live import decode_response
from .schema import canonical


BODY_KEYS = {
    "model", "messages", "temperature", "max_tokens", "stream",
    "response_format",
}


def _validate(body: Any, seconds: int, output_bytes: int) -> None:
    if not isinstance(body, dict) or set(body) != BODY_KEYS:
        raise ValueError("body_keys")
    if body["model"] != MODEL or body["stream"] is not False:
        raise ValueError("model_or_stream")
    if body["temperature"] != 0:
        raise ValueError("temperature")
    if type(body["max_tokens"]) is not int or not 1 <= body["max_tokens"] <= 4_096:
        raise ValueError("completion_limit")
    if body["response_format"] != {"type": "json_object"}:
        raise ValueError("response_format")
    if (
        not isinstance(body["messages"], list) or len(body["messages"]) != 2
        or any(
            not isinstance(row, dict) or set(row) != {"role", "content"}
            or row["role"] not in {"system", "user"}
            or not isinstance(row["content"], str)
            for row in body["messages"]
        )
    ):
        raise ValueError("messages")
    if type(seconds) is not int or not 10 <= seconds <= 180:
        raise ValueError("seconds")
    if type(output_bytes) is not int or not 1 <= output_bytes <= 65_536:
        raise ValueError("output_bytes")
    if len(canonical(body).encode()) > 1_000_000:
        raise ValueError("body_bytes")


def _default_client_builder(*, api_key, seconds, max_retries, trust_env):
    import httpx
    from openai import OpenAI

    timeout = httpx.Timeout(timeout=float(seconds - 2), connect=20.0)
    http_client = httpx.Client(
        timeout=timeout, trust_env=trust_env, follow_redirects=False,
    )
    return OpenAI(
        api_key=api_key, base_url=BASE_URL, timeout=timeout,
        max_retries=max_retries, http_client=http_client,
    )


def execute_one(
    body: dict[str, Any], *, seconds: int, output_bytes: int,
    credential_loader: Callable[[], str] = load_credential,
    client_builder: Callable[..., Any] = _default_client_builder,
) -> dict[str, Any]:
    """Execute one call and return only bounded response metadata."""
    client = None
    try:
        _validate(body, seconds, output_bytes)
        secret = credential_loader()
        client = client_builder(
            api_key=secret, seconds=seconds, max_retries=0, trust_env=False,
        )
        response = client.chat.completions.create(**body)
        if hasattr(response, "model_dump"):
            raw = response.model_dump()
        elif hasattr(response, "to_dict"):
            raw = response.to_dict()
        else:
            raise TypeError("provider_response")
        result = decode_response(canonical(raw), output_bytes)
        result["transport"] = "openai-httpx-single-attempt-v1"
        return result
    except ValueError as exc:
        return {"error": "worker_" + str(exc), "usage_source": "unavailable"}
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        error = "http_" + str(status) if type(status) is int else "transport_" + type(exc).__name__
        return {"error": error, "usage_source": "unavailable"}
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
