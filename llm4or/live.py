"""Approved AntChat transport: one POST per reserved attempt, no SDK retries.

The child alone reads the private profile. Credentials never enter its return
value or the ledger, and redirects are forbidden. No model tools are exposed.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3
import urllib.error
import urllib.request

from .gateway import Gateway, Limits, Stopped
from .schema import canonical, digest, loads

BASE_URL = "https://antchat.alipay.com/v1"
MODEL = "DeepSeek-V4-Pro-0813"
PROFILE = Path("/Users/chengxi-nju/ARK/.ark/config.yaml")
ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "results/private/pilot_s1_20260831"
AUTH_PATH = ROOT / "experiments/pilot_authorization.json"


@dataclass(frozen=True)
class LiveRequest:
    base_url: str = BASE_URL
    model: str = MODEL


def build_request(payload, limits):
    body = {"model": MODEL, "messages": [
        {"role": "system", "content": payload["instruction"]},
        {"role": "user", "content": canonical({k: v for k, v in payload.items() if k != "instruction"})}],
        "temperature": 0, "max_tokens": limits.completion_tokens,
        "stream": False, "response_format": {"type": "json_object"}}
    wire = canonical(body).encode()
    if len(wire) > limits.input_bytes:
        raise Stopped("wire_input_byte_limit")
    return wire


def load_credential():
    # Local parsing only; never execute config.py or export auth to the shell.
    import yaml
    if PROFILE.stat().st_mode & 0o077:
        raise Stopped("private_profile_permissions_not_600")
    config = yaml.safe_load(PROFILE.read_text())
    if config.get("openai_base_url", "").rstrip("/") != BASE_URL:
        raise Stopped("private_profile_endpoint_mismatch")
    if config.get("openai_model", "").removeprefix("openai/") != MODEL:
        raise Stopped("private_profile_model_mismatch")
    secret = config.get("openai_api_key")
    if not isinstance(secret, str) or not secret.strip() or "\n" in secret or "\r" in secret:
        raise Stopped("private_profile_missing_valid_key")
    return secret


def decode_response(raw, byte_limit):
    data = json.loads(raw)
    choices = data.get("choices")
    usage = data.get("usage")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(usage, dict):
        raise Stopped("provider_schema_or_usage_missing")
    choice = choices[0]
    text = choice.get("message", {}).get("content")
    if not isinstance(text, str):
        raise Stopped("provider_content_missing")
    # Keep only bounded, non-secret response metadata. Never retain raw headers
    # or errors. Reasoning text is not requested or persisted.
    result = {"text": text[:byte_limit], "prompt_tokens": usage.get("prompt_tokens"),
              "completion_tokens": usage.get("completion_tokens"),
              "total_tokens": usage.get("total_tokens"), "usage_source": "provider_reported",
              "finish_reason": choice.get("finish_reason"),
              "reported_model": str(data.get("model", ""))[:200],
              "response_id": str(data.get("id", ""))[:200],
              "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
              "cached_input_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
              "content_utf8_bytes": len(text.encode())}
    if len(text.encode()) > byte_limit:
        result["error"] = "output_byte_limit"
        result["text"] = ""
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Stopped("http_redirect_refused")


def _live_worker(pipe, payload, limits):
    result = None
    secret = None
    try:
        secret = load_credential()
        wire = build_request(payload, limits)
        request = urllib.request.Request(BASE_URL + "/chat/completions", data=wire,
                                         headers={"Authorization": "Bearer " + secret,
                                                  "Content-Type": "application/json"}, method="POST")
        opener = urllib.request.build_opener(NoRedirect())
        # urllib has no automatic HTTP/status retry. At most one request here.
        with opener.open(request, timeout=max(1, limits.request_seconds - 2)) as response:
            raw = response.read(256001)
        if len(raw) > 256000:
            raise Stopped("provider_envelope_byte_limit")
        result = decode_response(raw, limits.output_bytes)
        result["request_utf8_bytes"] = len(wire)
    except urllib.error.HTTPError as exc:
        # Preserve bounded error semantics without exposing a key echoed by server.
        try:
            error = json.loads(exc.read(4096)).get("error", {})
            message = str(error.get("message", "")) if isinstance(error, dict) else str(error)
        except Exception:
            message = ""
        result = {"error": "http_" + str(exc.code), "http_status": exc.code,
                  "provider_message": message[:800], "usage_source": "unavailable"}
    except Exception as exc:
        result = {"error": str(exc) if isinstance(exc, Stopped) else type(exc).__name__,
                  "usage_source": "unavailable"}
    finally:
        # Even an unexpected provider echo cannot put the credential into logs.
        serialized = canonical(result)
        if secret:
            serialized = serialized.replace(secret, "[REDACTED]")
        pipe.send_bytes(serialized.encode())
        pipe.close()


class LiveGateway(Gateway):
    mode = "approved_live_antchat_v1"

    def __init__(self, directory=RUN_DIR, limits=None, manifest=None):
        auth = loads(AUTH_PATH.read_text())
        limits = limits or Limits(requests=60, per_problem=6, request_seconds=90)
        if (auth.get("status") != "approved" or auth.get("endpoint") != BASE_URL
                or auth.get("model") != MODEL or Path(directory).resolve() != RUN_DIR.resolve()
                or auth.get("run_directory") != str(RUN_DIR)
                or limits.requests > 60 or limits.per_problem > 6
                or limits.completion_tokens > 2048 or limits.input_bytes > 24000
                or limits.output_bytes > 24000 or limits.request_seconds > 90
                or limits.run_seconds > 7200):
            raise Stopped("live_authorization_scope_mismatch")
        self.allowed_problems = set(auth["problem_ids"])
        self.auth_hash = digest(auth)
        super().__init__(directory, limits, {**(manifest or {}), "authorization_hash": self.auth_hash,
                                            "provider": asdict(LiveRequest())})
        with self._lock():
            with self._connect() as con:
                con.executescript("""
                    CREATE TRIGGER IF NOT EXISTS one_retry_per_problem
                    BEFORE INSERT ON attempts
                    WHEN NEW.key LIKE '%:retry1' AND EXISTS (
                        SELECT 1 FROM attempts WHERE problem=NEW.problem AND key LIKE '%:retry1'
                    ) BEGIN SELECT RAISE(ABORT, 'explicit_retry_limit'); END;
                """)

    def transport_identity(self, reply):
        if type(reply) is not LiveRequest or reply != LiveRequest():
            raise Stopped("unapproved_live_transport")
        return {"live": asdict(reply)}

    def preflight(self, payload, reply):
        if digest(loads(AUTH_PATH.read_text())) != self.auth_hash:
            raise Stopped("authorization_changed_or_revoked")
        if payload.get("problem", {}).get("id") not in self.allowed_problems:
            raise Stopped("problem_outside_authorized_pilot")
        build_request(payload, self.limits)

    def request(self, key, problem, phase, payload, reply):
        from .pipeline import PROMPTS
        if problem != payload.get("problem", {}).get("id") or phase not in PROMPTS:
            raise Stopped("live_request_scope_mismatch")
        if key not in {problem + ":" + phase, problem + ":" + phase + ":retry1"}:
            raise Stopped("unapproved_request_key")
        # One explicit retry across all phases of this problem, not one per phase.
        # This check and reservation share Gateway's lock via the SQL trigger below.
        try:
            return super().request(key, problem, phase, payload, reply)
        except sqlite3.IntegrityError as exc:
            raise Stopped("explicit_retry_limit_or_ledger_conflict") from exc

    def make_process(self, ctx, pipe, reply, payload):
        return ctx.Process(target=_live_worker, args=(pipe, payload, self.limits))

    def validate_response(self, response):
        if response.get("usage_source") != "provider_reported":
            raise Stopped("provider_usage_unavailable")
        if response.get("finish_reason") != "stop":
            raise Stopped("incomplete_response_" + str(response.get("finish_reason")))
        if response.get("total_tokens") != response["prompt_tokens"] + response["completion_tokens"]:
            raise Stopped("provider_usage_inconsistent")

    def summary(self):
        with self._connect() as con:
            rows = list(con.execute("SELECT * FROM attempts"))
        responses = [loads(r["response"]) for r in rows if r["response"]]
        usage = [r for r in responses if r.get("usage_source") == "provider_reported"]
        return {"mode": "live_antchat", "reserved_attempts_including_failures": len(rows),
                "complete": sum(r["status"] == "complete" for r in rows),
                "failed": sum(r["status"] == "failed" for r in rows),
                "outcome_unknown": sum(r["status"] == "reserved" for r in rows),
                "attempts_with_provider_usage": len(usage),
                "attempts_without_usage": len(rows) - len(usage),
                "provider_reported_prompt_tokens": sum(r.get("prompt_tokens", 0) or 0 for r in usage),
                "provider_reported_completion_tokens": sum(r.get("completion_tokens", 0) or 0 for r in usage),
                "provider_reported_total_tokens": sum(r.get("total_tokens", 0) or 0 for r in usage),
                "limit": self.limits.requests, "monetary_cost": None}
