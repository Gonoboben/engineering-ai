from __future__ import annotations

import base64
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from engineering_ai.models import (
    BenchmarkCase,
    ModelImageAttachment,
    ModelMessage,
    ModelMetrics,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolSpec,
    OllamaProvider,
    run_benchmark,
)
from engineering_ai.models.protocol import ModelProviderProtocolError


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._raw


class OllamaProviderTests(unittest.TestCase):
    def test_provider_rejects_non_loopback_urls(self) -> None:
        for url in (
            "http://192.168.1.10:11434",
            "http://example.com:11434",
            "https://127.0.0.1:11434",
            "http://127.0.0.1:11434/api",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                OllamaProvider(url)

    def test_chat_translates_stable_request_and_parses_response(self) -> None:
        provider = OllamaProvider()
        captured = []
        replies = iter(
            [
                {"version": "9.9.9-test"},
                {
                    "model": "test-model",
                    "message": {
                        "role": "assistant",
                        "content": '{"answer":42}',
                        "thinking": "synthetic reasoning",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "read_repository",
                                    "arguments": {"path": "README.md"},
                                }
                            }
                        ],
                    },
                    "done": True,
                    "done_reason": "stop",
                    "total_duration": 2_000_000_000,
                    "load_duration": 100_000_000,
                    "prompt_eval_count": 20,
                    "prompt_eval_duration": 500_000_000,
                    "eval_count": 10,
                    "eval_duration": 1_000_000_000,
                },
            ]
        )

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(next(replies))

        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        }
        tool = ModelToolSpec(
            name="read_repository",
            description="Read a repository file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )
        request = ModelRequest(
            model="test-model",
            messages=(ModelMessage("user", "Return the answer."),),
            tools=(tool,),
            response_schema=schema,
            temperature=0.0,
            seed=7,
            context_tokens=8192,
            max_output_tokens=256,
            reasoning_effort="high",
            keep_alive="0",
        )

        with patch("engineering_ai.models.ollama.urlopen", side_effect=fake_urlopen):
            response = provider.chat(request, timeout_seconds=30.0)

        self.assertEqual(response.provider, "ollama")
        self.assertEqual(response.runtime_version, "9.9.9-test")
        self.assertEqual(response.content, '{"answer":42}')
        self.assertEqual(response.thinking, "synthetic reasoning")
        self.assertEqual(response.done_reason, "stop")
        self.assertEqual(
            response.tool_calls,
            (ModelToolCall("read_repository", {"path": "README.md"}),),
        )
        self.assertEqual(response.metrics.output_tokens_per_second, 10.0)
        self.assertEqual(len(captured), 2)
        version_request, _ = captured[0]
        chat_request, chat_timeout = captured[1]
        self.assertTrue(version_request.full_url.endswith("/api/version"))
        self.assertTrue(chat_request.full_url.endswith("/api/chat"))
        self.assertEqual(chat_timeout, 30.0)
        body = json.loads(chat_request.data.decode("utf-8"))
        self.assertFalse(body["stream"])
        self.assertEqual(body["format"], schema)
        self.assertEqual(body["think"], "high")
        self.assertEqual(body["options"]["num_ctx"], 8192)
        self.assertEqual(body["options"]["num_predict"], 256)
        self.assertEqual(body["options"]["seed"], 7)
        self.assertEqual(body["tools"][0]["function"]["name"], "read_repository")

    def test_chat_serializes_explicit_images_inline_without_path_or_url_authority(self) -> None:
        provider = OllamaProvider()
        captured = []
        replies = iter(
            [
                {"version": "1.0-test"},
                {
                    "model": "vision-test",
                    "message": {"role": "assistant", "content": "{}"},
                    "done": True,
                    "done_reason": "stop",
                },
            ]
        )

        def fake_urlopen(request, timeout):
            captured.append(request)
            return FakeResponse(next(replies))

        image = ModelImageAttachment(
            source_ref="schematic:page-1",
            media_type="image/png",
            data=b"explicit-image-bytes",
        )
        request = ModelRequest(
            model="vision-test",
            messages=(ModelMessage("user", "Inspect.", images=(image,)),),
        )
        with patch("engineering_ai.models.ollama.urlopen", side_effect=fake_urlopen):
            provider.chat(request)

        body = json.loads(captured[1].data.decode("utf-8"))
        message = body["messages"][0]
        self.assertEqual(
            message["images"],
            [base64.b64encode(b"explicit-image-bytes").decode("ascii")],
        )
        self.assertNotIn("source_ref", message)
        self.assertNotIn("path", message)
        self.assertNotIn("url", message)

    def test_runtime_diagnostics_records_running_model_resource_fields(self) -> None:
        provider = OllamaProvider()
        replies = iter(
            [
                {
                    "models": [
                        {
                            "name": "candidate",
                            "size": 18_000_000_000,
                            "size_vram": 7_000_000_000,
                            "context_length": 8192,
                            "details": {"quantization_level": "Q4_K_M"},
                        }
                    ]
                },
                {"version": "1.2.3"},
            ]
        )
        with patch(
            "engineering_ai.models.ollama.urlopen",
            side_effect=lambda request, timeout: FakeResponse(next(replies)),
        ):
            snapshot = provider.runtime_diagnostics()
        self.assertEqual(snapshot["runtime_version"], "1.2.3")
        self.assertEqual(snapshot["running_models"][0]["size_vram"], 7_000_000_000)

    def test_malformed_tool_call_is_protocol_error(self) -> None:
        provider = OllamaProvider()
        replies = iter(
            [
                {"version": "1"},
                {
                    "model": "bad",
                    "message": {"content": "", "tool_calls": [{"broken": True}]},
                },
            ]
        )
        with patch(
            "engineering_ai.models.ollama.urlopen",
            side_effect=lambda request, timeout: FakeResponse(next(replies)),
        ), self.assertRaises(ModelProviderProtocolError):
            provider.chat(
                ModelRequest(model="bad", messages=(ModelMessage("user", "x"),))
            )


class FakeProvider:
    provider_name = "fake"

    def runtime_version(self):
        return "fake-1"

    def runtime_diagnostics(self):
        return {"provider": "fake", "runtime_version": "fake-1", "running_models": []}

    def chat(self, request, *, timeout_seconds=300.0):
        return ModelResponse(
            provider="fake",
            runtime_version="fake-1",
            model=request.model,
            content="42",
            done_reason="stop",
            metrics=ModelMetrics(eval_count=2, eval_duration_ns=1_000_000_000),
        )


class BenchmarkHarnessTests(unittest.TestCase):
    def test_benchmark_records_model_metrics_and_explicit_score(self) -> None:
        case = BenchmarkCase(
            case_id="answer-42",
            description="Synthetic deterministic answer",
            request=ModelRequest(
                model="candidate",
                messages=(ModelMessage("user", "Return 42"),),
            ),
            scorer=lambda response: (response.content.strip() == "42", "exact answer"),
        )
        records = run_benchmark(FakeProvider(), (case,))
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].passed)
        self.assertEqual(records[0].score_note, "exact answer")
        self.assertEqual(records[0].done_reason, "stop")
        self.assertEqual(records[0].metrics["eval_count"], 2)
        self.assertEqual(records[0].runtime_diagnostics["provider"], "fake")

    def test_model_request_is_immutable_for_provider_swaps(self) -> None:
        request = ModelRequest(
            model="model-a",
            messages=(ModelMessage("user", "same task"),),
            context_tokens=4096,
        )
        alternate = replace(request, model="model-b")
        self.assertEqual(request.messages, alternate.messages)
        self.assertEqual(request.context_tokens, alternate.context_tokens)
        self.assertNotEqual(request.model, alternate.model)


if __name__ == "__main__":
    unittest.main()
