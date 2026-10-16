"""No external network: test the actual HTTP worker with a fake opener."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from llm4or import live
from llm4or.fixtures import scenario
from llm4or.gateway import Limits, Stopped
from llm4or.pipeline import make_payload, quote_spans


def response(text='{}', finish='stop', prompt=10, completion=20):
    return {"model": live.MODEL, "id": "test_response", "choices": [{"message": {"content": text}, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}}


class Pipe:
    def send_bytes(self, value): self.data = value
    def close(self): pass


class LiveTests(unittest.TestCase):
    def payload(self): return make_payload(scenario()[0], "initial")

    def test_wire_request_limits_and_no_tools(self):
        raw = live.build_request(self.payload(), Limits())
        r = json.loads(raw)
        self.assertEqual(r["max_tokens"], 2048)
        self.assertEqual(r["model"], live.MODEL)
        self.assertFalse(r["stream"])
        self.assertNotIn("tools", r)

    def test_wire_size_includes_envelope(self):
        with self.assertRaisesRegex(Stopped, "wire_input_byte_limit"):
            live.build_request(self.payload(), Limits(input_bytes=1))

    def test_provider_decode(self):
        r = live.decode_response(json.dumps(response()), 24000)
        self.assertEqual(r["usage_source"], "provider_reported")
        self.assertEqual(r["total_tokens"], 30)

    def test_missing_usage_refused(self):
        r = response(); del r["usage"]
        with self.assertRaises(Stopped): live.decode_response(json.dumps(r), 24000)

    def test_large_output_preserves_usage(self):
        r = live.decode_response(json.dumps(response('x'*10)), 5)
        self.assertEqual(r["error"], "output_byte_limit")
        self.assertEqual(r["completion_tokens"], 20)

    def test_length_finish_fails_closed(self):
        r = live.decode_response(json.dumps(response(finish="length")), 24000)
        with self.assertRaisesRegex(Stopped, "incomplete_response_length"):
            live.LiveGateway.validate_response(None, r)

    def test_inconsistent_usage_refused(self):
        r = live.decode_response(json.dumps(response()), 24000); r["total_tokens"] = 4
        with self.assertRaisesRegex(Stopped, "inconsistent"):
            live.LiveGateway.validate_response(None, r)

    def test_redirect_refused(self):
        with self.assertRaisesRegex(Stopped, "redirect"):
            live.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.org")

    def test_worker_single_request_and_secret_redaction(self):
        secret = "fixture_secret_never_log"
        outer = self
        class Opener:
            count = 0
            def open(self, request, timeout):
                self.count += 1
                outer.assertEqual(request.full_url, live.BASE_URL + "/chat/completions")
                outer.assertEqual(request.get_header("Authorization"), "Bearer " + secret)
                return io.BytesIO(json.dumps(response(secret)).encode())
        opener, pipe = Opener(), Pipe()
        with patch.object(live, "load_credential", return_value=secret), patch.object(live.urllib.request, "build_opener", return_value=opener):
            live._live_worker(pipe, self.payload(), Limits())
        self.assertEqual(opener.count, 1)
        self.assertNotIn(secret, pipe.data.decode())

    def test_http_error_is_not_retried_or_secret_logged(self):
        secret = "fixture_secret_never_log"
        class Opener:
            count = 0
            def open(self, request, timeout):
                self.count += 1
                raise urllib.error.HTTPError(request.full_url, 429, "rate", {}, io.BytesIO(json.dumps({"error": {"message": secret}}).encode()))
        opener, pipe = Opener(), Pipe()
        with patch.object(live, "load_credential", return_value=secret), patch.object(live.urllib.request, "build_opener", return_value=opener):
            live._live_worker(pipe, self.payload(), Limits())
        self.assertEqual(opener.count, 1)
        self.assertEqual(json.loads(pipe.data)["http_status"], 429)
        self.assertNotIn(secret, pipe.data.decode())

    def test_bad_profile_never_reaches_network(self):
        pipe = Pipe()
        with patch.object(live, "load_credential", side_effect=Stopped("bad_profile")), patch.object(live.urllib.request, "build_opener") as opener:
            live._live_worker(pipe, self.payload(), Limits())
            opener.assert_not_called()
        self.assertEqual(json.loads(pipe.data)["error"], "bad_profile")

    def test_quote_offsets_are_mechanically_correct(self):
        text = "Mixture uses 0.5 hours. Next sentence! Last."
        for span in quote_spans(text):
            self.assertEqual(text[span["start"]:span["end"]], span["quote"])

    def test_live_authorization_and_retry_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, authpath = Path(tmp)/"run", Path(tmp)/"auth.json"
            authpath.write_text(json.dumps({"status":"approved", "endpoint":live.BASE_URL, "model":live.MODEL,
                                          "run_directory":str(directory), "problem_ids":["correction"]}))
            with patch.object(live, "RUN_DIR", directory), patch.object(live, "AUTH_PATH", authpath):
                gateway = live.LiveGateway(directory)
                with self.assertRaises(Stopped):
                    live.LiveGateway(directory, Limits(requests=61))
                with self.assertRaisesRegex(Stopped, "scope"):
                    gateway.request("other:initial", "other", "initial", self.payload(), live.LiveRequest())
                with gateway._connect() as con:
                    con.execute("INSERT INTO attempts(key,problem,phase,fingerprint,request,status,created) VALUES('correction:initial:retry1','correction','initial','h','{}','reserved',0)")
                with self.assertRaisesRegex(Stopped, "retry"):
                    gateway.request("correction:teacher_model:retry1", "correction", "teacher_model", self.payload(), live.LiveRequest())


if __name__ == '__main__': unittest.main()
