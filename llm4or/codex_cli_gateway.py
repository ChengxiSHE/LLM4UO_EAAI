"""Durable, authorization-bound Codex CLI transport for development runs.

The gateway uses the existing Codex login in place.  It never reads, copies,
or serializes credentials.  Every physical CLI invocation is durably reserved
before launch and bounded by a frozen plan, timeout, retry policy, and global
circuit breaker.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from jsonschema import Draft202012Validator, ValidationError

from .benchmark_inputs import payload_sha256, validate_public_input
from .formal_gateway import RequestUnavailable, atomic_text, failure_class
from .gateway import Stopped
from .run_interruption import RunInterrupted
from .schema import canonical, digest


VERSION = "codex-cli-gateway-v6"


class LocalRequestFailure(Stopped):
    """A predeclared local-format request exhausted its physical attempts."""


CLI_WRAPPER_SCHEMA = {
    "type": "object",
    "properties": {"payload": {"type": "string"}},
    "required": ["payload"],
    "additionalProperties": False,
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _event_usage(stdout):
    usage = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    if not usage:
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if type(input_tokens) is not int or type(output_tokens) is not int or min(input_tokens, output_tokens) < 0:
        return None
    return {"prompt_tokens": input_tokens, "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens}


def _diagnostic(stderr):
    """Retain bounded CLI diagnostics while redacting paths and token-like text."""
    value = stderr[-4000:]
    value = re.sub(r"/(?:Users|private|Applications|tmp)/\S+", "[path]", value)
    value = re.sub(r"\b[A-Za-z0-9_-]{32,}\b", "[redacted]", value)
    return value[-2000:]


def run_codex_cli(command, prompt, timeout):
    try:
        process = subprocess.run(
            command, input=prompt, text=True, capture_output=True, timeout=timeout,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return {"error": "transport_codex_cli_timeout"}
    stdout = process.stdout[-2_000_000:]
    stderr = process.stderr[-20_000:]
    if process.returncode:
        lowered = (stdout + "\n" + stderr).lower()
        transient = any(word in lowered for word in (
            "timeout", "timed out", "connection", "network", "rate limit", "429", "temporarily unavailable",
        ))
        if process.returncode == 2:
            return {"error": "codex_cli_argument_error"}
        return {"error": "transport_codex_cli_exit" if transient else "codex_cli_runtime_error",
                "diagnostic": _diagnostic(stderr)}
    return {"stdout": stdout}


def codex_cli_command(plan, workspace, schema_path, output_path):
    """Build the frozen non-interactive command without reading user config."""
    return [
        plan["codex_cli"], "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--strict-config", "--skip-git-repo-check", "--sandbox", "read-only",
        "-c", 'approval_policy="never"',
        "--model", plan["model"], "-c", "model_reasoning_effort=\"" + plan["reasoning_effort"] + "\"",
        "--disable", "shell_tool", "--disable", "apps", "--disable", "browser_use",
        "--disable", "computer_use", "--disable", "multi_agent", "--disable", "plugins",
        "--disable", "skill_search", "--json", "--output-schema", str(schema_path),
        "--output-last-message", str(output_path), "--cd", str(workspace), "-",
    ]


def validate_codex_cli_interface(plan, workspace):
    """Fail before reservation if the installed CLI rejects any frozen option."""
    workspace = Path(workspace)
    command = codex_cli_command(
        plan, workspace, workspace / "interface.schema.json", workspace / "interface.output.json",
    )
    process = subprocess.run(
        command[:-1] + ["--help"], capture_output=True, text=True, timeout=15,
        env=os.environ.copy(),
    )
    if process.returncode:
        raise Stopped("codex_cli_interface_invalid")


class CodexCliGateway:
    def __init__(self, root, plan, authorization_path, *, runner=run_codex_cli, test_mode=False):
        self.root = Path(root).resolve()
        self.plan = plan
        self.plan_hash = digest(plan)
        self.auth_path = self.root / authorization_path
        self.directory = (self.root / plan["run_directory"]).resolve()
        self.runner = runner
        self.test_mode = test_mode
        if not test_mode:
            self._approved()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.directory / "request_locks").mkdir(exist_ok=True)
        (self.directory / "request_payloads").mkdir(exist_ok=True)
        (self.directory / "codex_workspace").mkdir(exist_ok=True)
        self.db = self.directory / "requests.sqlite3"
        with self.connection() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, config TEXT, started REAL);
                CREATE TABLE IF NOT EXISTS scopes (id TEXT PRIMARY KEY, calls INTEGER, tokens INTEGER);
                CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, fingerprint TEXT, status TEXT,
                  charged INTEGER, response TEXT, response_hash TEXT, error TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS physical (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT,
                  ordinal INTEGER, status TEXT, reserved INTEGER, charged INTEGER, error TEXT, created REAL,
                  UNIQUE(key,ordinal));
                CREATE TABLE IF NOT EXISTS logical (scope TEXT, key TEXT, charged INTEGER, PRIMARY KEY(scope,key));
                CREATE TABLE IF NOT EXISTS slots (scope TEXT, slot INTEGER, key TEXT, PRIMARY KEY(scope,slot));
                CREATE TABLE IF NOT EXISTS halt (id INTEGER PRIMARY KEY, reason TEXT);
                CREATE TABLE IF NOT EXISTS work (scope TEXT PRIMARY KEY, stage TEXT, status TEXT, error TEXT, updated REAL);
                CREATE TABLE IF NOT EXISTS imports (source_db_sha256 TEXT PRIMARY KEY,
                  request_count INTEGER, charged INTEGER, imported REAL);
            """)
            config = canonical({"version": VERSION, "plan": self.plan_hash, "directory": str(self.directory)})
            old = database.execute("SELECT config FROM metadata WHERE id=1").fetchone()
            if old and old[0] != config:
                raise Stopped("codex_cli_ledger_configuration_changed")
            database.execute("INSERT OR IGNORE INTO metadata VALUES (1,?,?)", (config, time.time()))
            database.execute(
                "UPDATE physical SET status='failed',error='transport_process_interrupted' WHERE status='reserved'"
            )
            database.execute(
                "UPDATE requests SET status='failed',error='transport_process_interrupted' WHERE status='running'"
            )
        self._import_cache()
        self.write_progress()

    def _import_cache(self):
        binding = self.plan.get("cache_import")
        if not binding:
            return
        source = (self.root / binding["source_database"]).resolve()
        if self.root not in source.parents or source == self.db or _sha(source) != binding["source_db_sha256"]:
            raise Stopped("codex_cli_cache_import_source_changed")
        expected = {row["key"]: row for row in binding["entries"]}
        source_db = sqlite3.connect("file:" + str(source) + "?mode=ro", uri=True)
        source_db.row_factory = sqlite3.Row
        try:
            metadata = source_db.execute("SELECT config FROM metadata WHERE id=1").fetchone()
            if not metadata or json.loads(metadata["config"]).get("plan") != binding["source_plan_sha256"]:
                raise Stopped("codex_cli_cache_import_plan_changed")
            rows = source_db.execute(
                "SELECT key,fingerprint,charged,response,response_hash,created FROM requests "
                "WHERE status='complete' ORDER BY key"
            ).fetchall()
        finally:
            source_db.close()
        if {row["key"] for row in rows} != set(expected):
            raise Stopped("codex_cli_cache_import_set_changed")
        total = 0
        for row in rows:
            spec = expected[row["key"]]
            if (
                row["key"] != row["fingerprint"] or row["response_hash"] != spec["response_hash"]
                or row["charged"] != spec["charged"] or digest(json.loads(row["response"])) != row["response_hash"]
            ):
                raise Stopped("codex_cli_cache_import_integrity")
            total += row["charged"]
        if len(rows) != binding["request_count"] or total != binding["charged"]:
            raise Stopped("codex_cli_cache_import_accounting")
        with self.connection() as database:
            prior = database.execute("SELECT * FROM imports WHERE source_db_sha256=?", (
                binding["source_db_sha256"],
            )).fetchone()
            if prior and (prior["request_count"], prior["charged"]) != (len(rows), total):
                raise Stopped("codex_cli_cache_import_drift")
            for row in rows:
                old = database.execute("SELECT * FROM requests WHERE key=?", (row["key"],)).fetchone()
                if old and (
                    old["status"] != "complete" or old["response_hash"] != row["response_hash"]
                    or old["charged"] != row["charged"]
                ):
                    raise Stopped("codex_cli_cache_import_collision")
                database.execute(
                    "INSERT OR IGNORE INTO requests VALUES (?,?, 'complete', ?, ?, ?, NULL, ?)",
                    (row["key"], row["fingerprint"], row["charged"], row["response"],
                     row["response_hash"], row["created"]),
                )
            database.execute(
                "INSERT OR IGNORE INTO imports VALUES (?,?,?,?)",
                (binding["source_db_sha256"], len(rows), total, time.time()),
            )

    def _approved(self):
        auth = json.loads(self.auth_path.read_text())
        expected = {
            "schema": self.plan["authorization_schema"], "status": "approved",
            "plan_sha256": self.plan_hash, "model": self.plan["model"],
            "run_directory": str(self.root / self.plan["run_directory"]), "limits": self.plan["limits"],
        }
        if any(auth.get(key) != value for key, value in expected.items()) or not auth.get("user_confirmation"):
            raise Stopped("codex_cli_run_approval_required")
        for name, expected_hash in self.plan["frozen_files"].items():
            if _sha(self.root / name) != expected_hash:
                raise Stopped("frozen_file_changed:" + name)

    @contextmanager
    def connection(self):
        database = sqlite3.connect(self.db, timeout=30)
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA synchronous=FULL")
        database.execute("PRAGMA busy_timeout=30000")
        try:
            with database:
                yield database
        finally:
            database.close()

    @contextmanager
    def lock(self, key):
        with (self.directory / "request_locks" / (digest(key) + ".lock")).open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def register(self, scope, calls, tokens):
        parts = scope.split(":")
        contract = self.plan.get("scope_contract", {
            "prefix": "v8dev", "method": "IndexedProbe", "calls_per_scope": 2,
        })
        selected = {row["problem_id"] for row in self.plan["selection"]["records"]}
        if (
            len(parts) != 4 or parts[0] != contract["prefix"] or parts[1] != contract["method"]
            or int(parts[2]) not in self.plan["replicates"] or parts[3] not in selected
            or calls != contract["calls_per_scope"] or tokens != self.plan["token_cap"]
        ):
            raise Stopped("codex_cli_scope_not_authorized")
        with self.connection() as database:
            old = database.execute("SELECT calls,tokens FROM scopes WHERE id=?", (scope,)).fetchone()
            if old and tuple(old) != (calls, tokens):
                raise Stopped("codex_cli_trajectory_changed")
            database.execute("INSERT OR IGNORE INTO scopes VALUES (?,?,?)", (scope, calls, tokens))

    def _command(self, schema_path, output_path):
        return codex_cli_command(
            self.plan, self.directory / "codex_workspace", schema_path, output_path,
        )

    def request(self, scope, payload, prefix, replicate, slot=0):
        self._approved() if not self.test_mode else None
        import shutil
        if shutil.disk_usage(self.directory).free < self.plan["limits"]["minimum_free_disk_bytes"]:
            raise RunInterrupted("global_disk_guard")
        with self.connection() as database:
            started = database.execute("SELECT started FROM metadata WHERE id=1").fetchone()[0]
        if time.time() - started > self.plan["limits"]["max_run_seconds"]:
            raise RunInterrupted("run_time_limit")
        public = validate_public_input(payload.get("problem"))
        if public["id"] != scope.split(":")[-1] or payload_sha256(public) != self.plan["public_inputs"][public["id"]]:
            raise Stopped("codex_cli_public_payload_changed")
        if set(payload) != {"version", "instruction", "problem", "context", "output_contract", "response_schema"}:
            raise Stopped("codex_cli_payload_shape")
        calls_per_scope = self.plan.get("scope_contract", {"calls_per_scope": 2})["calls_per_scope"]
        if replicate not in self.plan["replicates"] or type(slot) is not int or not 0 <= slot < calls_per_scope:
            raise Stopped("codex_cli_slot_or_replicate")
        envelope = self.plan.get("transport", {}).get("prompt_envelope", "full_payload")
        if envelope == "full_payload":
            prompt = payload["instruction"] + (
                "\n\nReturn one JSON object with exactly one key named payload. Its value must be a JSON-serialized "
                "string containing only the object required by this payload:\n"
            ) + canonical({
                key: value for key, value in payload.items() if key != "instruction"
            })
        elif envelope == "official_text_wrapper":
            if payload["response_schema"] != {
                "type": "object", "properties": {"text": {"type": "string"}},
                "required": ["text"], "additionalProperties": False,
            }:
                raise Stopped("codex_cli_official_text_schema_changed")
            # Keep the author prompt byte-exact up to this transport boundary.
            # Public-input and accounting metadata remain hashed in the
            # controller but are not duplicated into the model-visible text.
            prompt = payload["instruction"] + (
                "\n\nTransport only: return one JSON object with exactly one key named payload. "
                "Its value must be a JSON-serialized object with exactly one string key named text; "
                "put your complete answer in text."
            )
        else:
            raise Stopped("codex_cli_unknown_prompt_envelope")
        prompt_bytes = len(prompt.encode())
        if prompt_bytes > self.plan["limits"]["max_input_bytes"]:
            raise Stopped("codex_cli_input_byte_limit")
        reserve = prompt_bytes + self.plan["limits"]["token_overhead_reserve"] + self.plan["limits"]["max_completion_tokens"]
        fingerprint = digest({
            "prompt": prompt, "schema": payload["response_schema"], "prefix": prefix, "replicate": replicate,
            "model": self.plan["model"], "reasoning_effort": self.plan["reasoning_effort"],
        })
        key = fingerprint
        with self.lock(key):
            with self.connection() as database:
                halt = database.execute("SELECT reason FROM halt WHERE id=1").fetchone()
                if halt:
                    raise RunInterrupted("global_halt:" + halt[0])
                limits = database.execute("SELECT calls,tokens FROM scopes WHERE id=?", (scope,)).fetchone()
                if not limits:
                    raise Stopped("codex_cli_unregistered_scope")
                previous = database.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
                used = database.execute(
                    "SELECT count(*),coalesce(sum(charged),0) FROM logical WHERE scope=?", (scope,)
                ).fetchone()
                if not database.execute("SELECT 1 FROM logical WHERE scope=? AND key=?", (scope, key)).fetchone():
                    if used[0] >= limits[0] or used[1] + reserve > limits[1]:
                        raise Stopped("codex_cli_trajectory_budget_exhausted")
                old_slot = database.execute("SELECT key FROM slots WHERE scope=? AND slot=?", (scope, slot)).fetchone()
                if old_slot and old_slot[0] != key:
                    raise Stopped("codex_cli_resumed_request_drift")
                database.execute("INSERT OR IGNORE INTO slots VALUES (?,?,?)", (scope, slot, key))
                if previous and previous["status"] == "complete":
                    response = json.loads(previous["response"])
                    if digest(response) != previous["response_hash"]:
                        raise Stopped("codex_cli_cache_integrity")
                    database.execute("INSERT OR IGNORE INTO logical VALUES (?,?,?)", (scope, key, previous["charged"]))
                    return response
                if previous and previous["status"] == "exhausted":
                    if previous["error"] in self.plan["resilience"].get("retryable_local_errors", []):
                        raise LocalRequestFailure("method_failure:" + previous["error"])
                    raise RequestUnavailable("request_unavailable:" + (previous["error"] or "exhausted"))
                if not previous:
                    database.execute(
                        "INSERT INTO requests VALUES (?,?,'running',?,NULL,NULL,NULL,?)",
                        (key, fingerprint, reserve, time.time()),
                    )
                    database.execute("INSERT INTO logical VALUES (?,?,?)", (scope, key, reserve))
            payload_path = self.directory / "request_payloads" / (key + ".json")
            atomic_text(payload_path, canonical({
                "scope_first_use": scope, "payload": payload, "prefix": prefix,
                "replicate": replicate, "fingerprint": fingerprint,
            }))
            schema_path = self.directory / "request_payloads" / (key + ".schema.json")
            atomic_text(schema_path, canonical(payload["response_schema"]))
            cli_schema_path = self.directory / "request_payloads" / (key + ".cli.schema.json")
            atomic_text(cli_schema_path, canonical(CLI_WRAPPER_SCHEMA))
            output_path = self.directory / "request_payloads" / (key + ".response.json")
            with self.connection() as database:
                prior_physical = database.execute("SELECT count(*) FROM physical WHERE key=?", (key,)).fetchone()[0]
            ordinal = prior_physical + 1
            policy = self.plan["resilience"]
            while ordinal <= policy["max_attempts_per_request"]:
                with self.connection() as database:
                    physical_count, physical_tokens = database.execute(
                        "SELECT count(*),coalesce(sum(charged),0) FROM physical"
                    ).fetchone()
                    if (physical_count >= self.plan["limits"]["max_requests"] or
                            physical_tokens + reserve > self.plan["limits"]["max_total_reserved_or_reported_tokens"]):
                        raise RunInterrupted("global_budget_exhausted")
                    database.execute(
                        "INSERT INTO physical(key,ordinal,status,reserved,charged,error,created) "
                        "VALUES (?,?,'reserved',?,?,NULL,?)", (key, ordinal, reserve, reserve, time.time()),
                    )
                if output_path.exists():
                    output_path.unlink()
                result = self.runner(
                    self._command(cli_schema_path, output_path), prompt,
                    self.plan["limits"]["request_seconds"]
                )
                error = result.get("error")
                if error and result.get("diagnostic"):
                    diagnostic_directory = self.directory / "diagnostics"
                    diagnostic_directory.mkdir(exist_ok=True, mode=0o700)
                    atomic_text(
                        diagnostic_directory / f"{key}.{ordinal}.json",
                        canonical({"error": error, "diagnostic": result["diagnostic"]}),
                    )
                response = None
                charge = reserve
                if not error:
                    try:
                        text = output_path.read_text()
                        if len(text.encode()) > self.plan["limits"]["max_output_bytes"]:
                            raise ValueError("output_byte_limit")
                        wrapper = json.loads(text)
                        if set(wrapper) != {"payload"} or not isinstance(wrapper["payload"], str):
                            raise ValueError("invalid_cli_wrapper")
                        parsed = json.loads(wrapper["payload"])
                        if not isinstance(parsed, dict):
                            raise ValueError("response_not_object")
                        Draft202012Validator(payload["response_schema"]).validate(parsed)
                        usage = _event_usage(result.get("stdout", ""))
                        if usage:
                            charge = usage["total_tokens"]
                        response = {
                            "text": canonical(parsed),
                            "prompt_tokens": usage["prompt_tokens"] if usage else reserve,
                            "completion_tokens": usage["completion_tokens"] if usage else 0,
                            "total_tokens": charge,
                            "finish_reason": "stop", "reported_model": self.plan["model"],
                        }
                    except (OSError, ValueError, TypeError, ValidationError):
                        error = "invalid_json_response"
                with self.connection() as database:
                    database.execute(
                        "UPDATE physical SET status=?,charged=?,error=? WHERE key=? AND ordinal=?",
                        ("failed" if error else "complete", charge, error, key, ordinal),
                    )
                    aggregate = database.execute(
                        "SELECT coalesce(sum(charged),0) FROM physical WHERE key=?", (key,)
                    ).fetchone()[0]
                    database.execute("UPDATE logical SET charged=? WHERE key=?", (aggregate, key))
                    if error:
                        database.execute(
                            "UPDATE requests SET status='failed',charged=?,error=? WHERE key=?",
                            (aggregate, error, key),
                        )
                    else:
                        database.execute(
                            "UPDATE requests SET status='complete',charged=?,response=?,response_hash=?,error=NULL WHERE key=?",
                            (aggregate, canonical(response), digest(response), key),
                        )
                    kind = failure_class(error) if error else None
                    if error in policy.get("retryable_local_errors", []):
                        kind = "item_retryable"
                    recent = database.execute(
                        "SELECT error FROM physical ORDER BY id DESC LIMIT ?",
                        (policy["circuit_breaker_consecutive_failures"],),
                    ).fetchall()
                    circuit = bool(error and kind == "retryable" and len(recent) == policy["circuit_breaker_consecutive_failures"]
                                   and all(row[0] and failure_class(row[0]) == "retryable" for row in recent))
                    if kind == "fatal" or circuit:
                        reason = error if kind == "fatal" else "circuit_breaker_transport_failures"
                        database.execute("INSERT OR REPLACE INTO halt VALUES (1,?)", (reason,))
                    if not error and charge > reserve:
                        database.execute(
                            "INSERT OR REPLACE INTO halt VALUES (1,'codex_cli_token_reservation_overrun')"
                        )
                self.write_progress(scope)
                if not error:
                    return response
                if kind == "local":
                    with self.connection() as database:
                        database.execute("UPDATE requests SET status='exhausted' WHERE key=?", (key,))
                    raise Stopped(error)
                if kind == "fatal" or circuit:
                    raise RunInterrupted("global_halt:" + (error if kind == "fatal" else "circuit_breaker_transport_failures"))
                if ordinal >= policy["max_attempts_per_request"]:
                    with self.connection() as database:
                        database.execute("UPDATE requests SET status='exhausted' WHERE key=?", (key,))
                    if kind == "item_retryable":
                        raise LocalRequestFailure("method_failure:" + error)
                    raise RequestUnavailable("request_unavailable:" + error)
                delay = policy["backoff_seconds"][min(ordinal-1, len(policy["backoff_seconds"])-1)] \
                    if policy["backoff_seconds"] else 0
                if delay and not self.test_mode:
                    time.sleep(delay)
                ordinal += 1
        raise Stopped("codex_cli_unreachable")

    def scope_usage(self, scope):
        with self.connection() as database:
            row = database.execute(
                "SELECT count(*),coalesce(sum(charged),0) FROM logical WHERE scope=?", (scope,)
            ).fetchone()
        return {"logical_requests": row[0], "logical_tokens": row[1]}

    def work_started(self, scope):
        with self.connection() as database:
            database.execute(
                "INSERT OR REPLACE INTO work VALUES (?,?,?,?,?)",
                (scope, scope.split(":", 1)[0], "running", None, time.time()),
            )
        self.write_progress(scope)

    def work_finished(self, scope, status, error=None):
        with self.connection() as database:
            database.execute(
                "INSERT OR REPLACE INTO work VALUES (?,?,?,?,?)",
                (scope, scope.split(":", 1)[0], status, error, time.time()),
            )
        self.write_progress(scope)

    def halt_reason(self):
        with self.connection() as database:
            row = database.execute("SELECT reason FROM halt WHERE id=1").fetchone()
        return row[0] if row else None

    def summary(self):
        with self.connection() as database:
            physical, tokens = database.execute(
                "SELECT count(*),coalesce(sum(charged),0) FROM physical"
            ).fetchone()
            complete = database.execute("SELECT count(*) FROM physical WHERE status='complete'").fetchone()[0]
            retries = database.execute("SELECT count(*) FROM physical WHERE ordinal>1").fetchone()[0]
            logical = database.execute("SELECT count(*),coalesce(sum(charged),0) FROM logical").fetchone()
            work = dict(database.execute("SELECT status,count(*) FROM work GROUP BY status"))
            imported = database.execute(
                "SELECT coalesce(sum(request_count),0),coalesce(sum(charged),0) FROM imports"
            ).fetchone()
        return {
            "mode": "codex_cli_chatgpt_quota", "physical_attempts": physical,
            "completed_physical_attempts": complete, "retry_attempts": retries,
            "physical_reserved_or_reported_tokens": tokens,
            "logical_requests": logical[0], "logical_reserved_or_reported_tokens": logical[1],
            "model": self.plan["model"], "reasoning_effort": self.plan["reasoning_effort"],
            "max_concurrent_requests": self.plan["resilience"]["max_concurrent_requests"],
            "work": work, "halt": self.halt_reason(),
            "imported_requests": imported[0], "imported_charged_tokens": imported[1],
        }

    def write_progress(self, current_scope=None):
        if not hasattr(self, "db"):
            return
        value = {"plan_sha256": self.plan_hash, "current_scope": current_scope, **self.summary()}
        atomic_text(self.directory / "progress.json", json.dumps(value, sort_keys=True, separators=(",", ":")))


__all__ = [
    "CodexCliGateway", "LocalRequestFailure", "VERSION", "codex_cli_command", "run_codex_cli",
    "validate_codex_cli_interface",
]
