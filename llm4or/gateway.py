"""Durable, fail-closed request accounting; the default gateway is offline only.

Reservations survive crashes; an ambiguous attempt is never automatically retried.
There is deliberately no network provider, credential reader or live-enable switch.
"""
from dataclasses import asdict, dataclass
from contextlib import contextmanager
import fcntl
import multiprocessing
from pathlib import Path
import sqlite3
import time

from .schema import canonical, digest, loads


class Stopped(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    requests: int = 60
    per_problem: int = 6
    input_bytes: int = 24000
    output_bytes: int = 24000
    completion_tokens: int = 2048
    request_seconds: float = 30
    run_seconds: float = 7200

    def __post_init__(self):
        for name in ("requests", "per_problem", "input_bytes", "output_bytes", "completion_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError("positive integer limit required")
        for name in ("request_seconds", "run_seconds"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or not 0 < v <= 86400:
                raise ValueError("finite duration required")


@dataclass(frozen=True)
class MockReply:
    """A fixed response, never an API response. Token counts are simulated."""
    text: str
    delay: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    fail: bool = False


def _mock_worker(pipe, reply, byte_limit):
    try:
        time.sleep(reply.delay)
        if reply.fail:
            pipe.send_bytes(canonical({"error": "mock_transport_failure"}).encode())
        elif len(reply.text.encode()) > byte_limit:
            pipe.send_bytes(canonical({"error": "output_byte_limit"}).encode())
        else:
            pipe.send_bytes(canonical({"text": reply.text, "prompt_tokens": reply.prompt_tokens,
                                       "completion_tokens": reply.completion_tokens,
                                       "usage_source": "simulated"}).encode())
    finally:
        pipe.close()


class Gateway:
    mode = "offline_only_v1"

    def __init__(self, directory, limits=Limits(), manifest=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.limits = limits
        self.db = self.directory / "requests.sqlite3"
        self.config = {"limits": asdict(limits), "manifest": manifest or {}, "mode": self.mode}
        with self._lock():
            with self._connect() as con:
                con.executescript("""
                    CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, config TEXT, started REAL);
                    CREATE TABLE IF NOT EXISTS attempts (
                        key TEXT PRIMARY KEY, problem TEXT NOT NULL, phase TEXT NOT NULL,
                        fingerprint TEXT NOT NULL, request TEXT NOT NULL,
                        status TEXT NOT NULL, response TEXT, response_hash TEXT,
                        error TEXT, created REAL NOT NULL, finished REAL
                    );
                """)
                row = con.execute("SELECT config FROM metadata WHERE id=1").fetchone()
                if row and row[0] != canonical(self.config):
                    raise Stopped("run configuration changed; cannot reset counters")
                if not row:
                    con.execute("INSERT INTO metadata VALUES (1, ?, ?)", (canonical(self.config), time.time()))

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db, timeout=1)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA synchronous=FULL")
        try:
            with con:
                yield con
        finally:
            con.close()

    def _lock(self):
        class Lock:
            def __enter__(inner):
                inner.file = (self.directory / "run.lock").open("a")
                try:
                    fcntl.flock(inner.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    inner.file.close()
                    raise Stopped("another request is active") from None
                return inner

            def __exit__(inner, *args):
                inner.file.close()
        return Lock()

    def transport_identity(self, reply):
        if type(reply) is not MockReply:
            raise Stopped("only offline fixed responses are implemented")
        return {"mock": asdict(reply)}

    def preflight(self, payload, reply):
        pass

    def make_process(self, ctx, pipe, reply, payload):
        return ctx.Process(target=_mock_worker, args=(pipe, reply, self.limits.output_bytes))

    def validate_response(self, response):
        pass

    def request(self, key, problem, phase, payload, reply):
        identity = self.transport_identity(reply)
        self.preflight(payload, reply)
        if any(not isinstance(v, str) or not 0 < len(v) <= 200 for v in (key, problem, phase)):
            raise Stopped("invalid request identity")
        body = canonical(payload)
        if len(body.encode()) > self.limits.input_bytes:
            raise Stopped("input_byte_limit")
        fingerprint = digest({"payload": payload, "problem": problem, "phase": phase, **identity})
        with self._lock():
            with self._connect() as con:
                existing = con.execute("SELECT * FROM attempts WHERE key=?", (key,)).fetchone()
                if existing:
                    if existing["fingerprint"] != fingerprint or existing["request"] != body:
                        raise Stopped("logical request key reused for different content")
                    if existing["status"] == "complete":
                        response = loads(existing["response"])
                        if digest(response) != existing["response_hash"]:
                            raise Stopped("cached response integrity failure")
                        return response
                    raise Stopped("prior attempt " + existing["status"] + "; explicit new retry key required")
                count = con.execute("SELECT count(*) FROM attempts").fetchone()[0]
                per = con.execute("SELECT count(*) FROM attempts WHERE problem=?", (problem,)).fetchone()[0]
                started = con.execute("SELECT started FROM metadata WHERE id=1").fetchone()[0]
                remaining = started + self.limits.run_seconds - time.time()
                if count >= self.limits.requests or per >= self.limits.per_problem:
                    raise Stopped("request_limit")
                if remaining <= 0:
                    raise Stopped("run_wall_limit")
                con.execute("INSERT INTO attempts(key,problem,phase,fingerprint,request,status,created) VALUES(?,?,?,?,?,'reserved',?)",
                            (key, problem, phase, fingerprint, body, time.time()))
            # The transaction has committed BEFORE the transport process starts.
            ctx = multiprocessing.get_context("spawn")
            receive, send = ctx.Pipe(duplex=False)
            process = self.make_process(ctx, send, reply, payload)
            response, error = None, None
            try:
                process.start()
                send.close()
                if not receive.poll(min(self.limits.request_seconds, remaining)):
                    raise Stopped("request_timeout_outcome_unknown")
                response = loads(receive.recv_bytes(6 * self.limits.output_bytes + 4096).decode())
                if "error" in response:
                    raise Stopped(response["error"])
                for name in ("prompt_tokens", "completion_tokens"):
                    if type(response[name]) is not int or response[name] < 0:
                        raise Stopped("invalid_usage")
                if response["completion_tokens"] > self.limits.completion_tokens:
                    raise Stopped("completion_token_limit")
                if len(response["text"].encode()) > self.limits.output_bytes:
                    raise Stopped("output_byte_limit")
                self.validate_response(response)
            except Exception as exc:
                error = str(exc) if isinstance(exc, Stopped) else type(exc).__name__
            finally:
                if process.pid is not None:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=2)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=2)
                receive.close()
                send.close()
            with self._connect() as con:
                con.execute("UPDATE attempts SET status=?,response=?,response_hash=?,error=?,finished=? WHERE key=?",
                            ("failed" if error else "complete", canonical(response) if response else None,
                             digest(response) if response else None, error, time.time(), key))
            if error:
                raise Stopped(error)
            return response

    def summary(self):
        with self._connect() as con:
            rows = list(con.execute("SELECT status,response,error FROM attempts"))
        usages = [loads(r["response"]) for r in rows if r["response"]]
        return {"mode": "offline_only", "attempts_including_failures": len(rows),
                "complete": sum(r["status"] == "complete" for r in rows),
                "reserved_outcome_unknown": sum(r["status"] == "reserved" for r in rows),
                "failed": sum(r["status"] == "failed" for r in rows),
                "simulated_prompt_tokens": sum(v.get("prompt_tokens", 0) for v in usages),
                "simulated_completion_tokens": sum(v.get("completion_tokens", 0) for v in usages),
                "actual_api_requests": 0, "monetary_cost": None}
