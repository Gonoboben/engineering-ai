"""Loopback-only Ollama provider.

This module transports model requests and returns advisory model output. It does
not execute tool calls and has no authority to alter Supervisor policy/state.
"""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from engineering_ai.models.protocol import (
    ModelProviderProtocolError,
    ModelProviderUnavailable,
)
from engineering_ai.models.types import (
    ModelMetrics,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
)


class OllamaProvider:
    provider_name = "ollama"
    _LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http":
            raise ValueError("Gate 005 local provider requires plain HTTP over loopback")
        if parsed.hostname not in self._LOOPBACK_HOSTS:
            raise ValueError("Gate 005 Ollama provider must use localhost/loopback only")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url must not include credentials, query, or fragment")
        if parsed.path not in ("", "/"):
            raise ValueError("base_url must not include an API path")
        self._base_url = base_url.rstrip("/")
        self._version_cache: str | None = None

    @property
    def base_url(self) -> str:
        return self._base_url

    def runtime_version(self) -> str | None:
        if self._version_cache is not None:
            return self._version_cache
        payload = self._request_json("GET", "/api/version", None, timeout_seconds=10.0)
        version = payload.get("version")
        if version is not None and not isinstance(version, str):
            raise ModelProviderProtocolError("Ollama version response contains non-string version")
        self._version_cache = version
        return version

    def chat(self, request: ModelRequest, *, timeout_seconds: float = 300.0) -> ModelResponse:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not request.messages:
            raise ValueError("model request requires at least one message")

        body: dict[str, Any] = {
            "model": request.model,
            "messages": [self._message_payload(message) for message in request.messages],
            "stream": False,
            "keep_alive": request.keep_alive,
            "options": {"temperature": request.temperature},
        }
        if request.seed is not None:
            body["options"]["seed"] = request.seed
        if request.context_tokens is not None:
            if request.context_tokens <= 0:
                raise ValueError("context_tokens must be positive")
            body["options"]["num_ctx"] = request.context_tokens
        if request.max_output_tokens is not None:
            if request.max_output_tokens <= 0:
                raise ValueError("max_output_tokens must be positive")
            body["options"]["num_predict"] = request.max_output_tokens
        if request.response_schema is not None:
            body["format"] = dict(request.response_schema)
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": dict(tool.parameters),
                    },
                }
                for tool in request.tools
            ]
        if request.reasoning_effort is not None:
            body["think"] = (
                False if request.reasoning_effort == "none" else request.reasoning_effort
            )

        version = self.runtime_version()
        payload = self._request_json(
            "POST", "/api/chat", body, timeout_seconds=timeout_seconds
        )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ModelProviderProtocolError("Ollama chat response missing message object")
        content = message.get("content", "")
        thinking = message.get("thinking", "")
        if not isinstance(content, str) or not isinstance(thinking, str):
            raise ModelProviderProtocolError("Ollama message content/thinking must be strings")

        tool_calls: list[ModelToolCall] = []
        raw_calls = message.get("tool_calls", []) or []
        if not isinstance(raw_calls, list):
            raise ModelProviderProtocolError("Ollama tool_calls must be a list")
        for raw_call in raw_calls:
            try:
                function = raw_call["function"]
                name = function["name"]
                arguments = function.get("arguments", {})
            except (KeyError, TypeError) as exc:
                raise ModelProviderProtocolError("Malformed Ollama tool call") from exc
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ModelProviderProtocolError("Malformed Ollama tool-call fields")
            tool_calls.append(ModelToolCall(name=name, arguments=arguments))

        metrics = ModelMetrics(
            total_duration_ns=self._optional_int(payload, "total_duration"),
            load_duration_ns=self._optional_int(payload, "load_duration"),
            prompt_eval_count=self._optional_int(payload, "prompt_eval_count"),
            prompt_eval_duration_ns=self._optional_int(payload, "prompt_eval_duration"),
            eval_count=self._optional_int(payload, "eval_count"),
            eval_duration_ns=self._optional_int(payload, "eval_duration"),
        )
        raw_metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"message"}
        }
        return ModelResponse(
            provider=self.provider_name,
            runtime_version=version,
            model=str(payload.get("model", request.model)),
            content=content,
            thinking=thinking,
            tool_calls=tuple(tool_calls),
            done_reason=(
                str(payload["done_reason"]) if payload.get("done_reason") is not None else None
            ),
            metrics=metrics,
            raw_metadata=raw_metadata,
        )

    @staticmethod
    def _message_payload(message: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.name is not None:
            payload["name"] = message.name
        return payload

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ModelProviderProtocolError(f"Ollama {key} must be an integer")
        return value

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        *,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            self._base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ModelProviderUnavailable(f"Ollama request failed: {exc}") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelProviderProtocolError("Ollama returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ModelProviderProtocolError("Ollama response must be a JSON object")
        return payload
