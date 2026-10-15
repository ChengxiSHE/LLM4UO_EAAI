import unittest

from llm4or.openai_httpx_worker import execute_one


BODY = {
    "model": "DeepSeek-V4-Flash",
    "messages": [
        {"role": "system", "content": "return json"},
        {"role": "user", "content": "{}"},
    ],
    "temperature": 0, "max_tokens": 128, "stream": False,
    "response_format": {"type": "json_object"},
}


class Response:
    def model_dump(self):
        return {
            "id": "response-1", "model": "DeepSeek-V4-Flash",
            "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
        }


class Completions:
    def __init__(self, calls): self.calls = calls
    def create(self, **kwargs): self.calls.append(kwargs); return Response()


class FakeClient:
    def __init__(self, calls):
        self.calls = calls
        self.chat = type("Chat", (), {"completions": Completions(calls)})()
        self.closed = False
    def close(self): self.closed = True


class OpenAIHttpxWorkerTests(unittest.TestCase):
    def test_single_call_returns_bounded_provider_metadata_and_closes_client(self):
        calls = []
        client = FakeClient(calls)
        builders = []
        def builder(**kwargs): builders.append(kwargs); return client
        result = execute_one(
            BODY, seconds=30, output_bytes=10_000,
            credential_loader=lambda: "secret-never-returned", client_builder=builder,
        )
        self.assertEqual(calls, [BODY])
        self.assertEqual(builders[0]["max_retries"], 0)
        self.assertFalse(builders[0]["trust_env"])
        self.assertEqual(result["text"], '{"ok":true}')
        self.assertEqual(result["total_tokens"], 7)
        self.assertEqual(result["reported_model"], "DeepSeek-V4-Flash")
        self.assertTrue(client.closed)
        self.assertNotIn("secret-never-returned", repr(result))

    def test_exception_is_classified_without_exception_text_or_secret(self):
        class ExplodingClient(FakeClient):
            def __init__(self):
                self.closed = False
                class Broken:
                    def create(self, **kwargs):
                        raise RuntimeError("secret-never-returned")
                self.chat = type("Chat", (), {"completions": Broken()})()
            def close(self): self.closed = True
        client = ExplodingClient()
        result = execute_one(
            BODY, seconds=30, output_bytes=10_000,
            credential_loader=lambda: "secret-never-returned",
            client_builder=lambda **kwargs: client,
        )
        self.assertEqual(result, {"error": "transport_RuntimeError", "usage_source": "unavailable"})
        self.assertTrue(client.closed)
        self.assertNotIn("secret-never-returned", repr(result))

    def test_rejects_streaming_model_or_unbounded_body_before_client_creation(self):
        for changed in (
            {**BODY, "stream": True},
            {**BODY, "model": "other"},
            {**BODY, "extra": 1},
        ):
            with self.subTest(changed=changed):
                result = execute_one(
                    changed, seconds=30, output_bytes=10_000,
                    credential_loader=lambda: self.fail("credential read"),
                    client_builder=lambda **kwargs: self.fail("client built"),
                )
                self.assertEqual(result["usage_source"], "unavailable")
                self.assertTrue(result["error"].startswith("worker_"))


if __name__ == "__main__":
    unittest.main()
