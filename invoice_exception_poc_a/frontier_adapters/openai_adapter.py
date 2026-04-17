"""OpenAI adapter implementation for bounded frontier inference."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from typing import Any

from invoice_exception_poc_a.frontier_adapters.base import FrontierAdapter
from invoice_exception_poc_a.frontier_adapters.model import (
    FrontierJudgmentRequest,
    FrontierJudgmentResponse,
)


class OpenAIFrontierAdapter(FrontierAdapter):
    """Concrete OpenAI adapter hook behind the provider-agnostic interface."""

    provider_name = "openai"

    def __init__(
        self,
        response_transport: Callable[[FrontierJudgmentRequest], FrontierJudgmentResponse] | None = None,
        client_factory: Callable[[str, int | None], Any] | None = None,
    ) -> None:
        self._response_transport = response_transport
        self._client_factory = client_factory

    def generate_judgment(self, request: FrontierJudgmentRequest) -> FrontierJudgmentResponse:
        """Use an injected transport for tests, or execute one bounded OpenAI response call."""
        if self._response_transport is not None:
            return self._response_transport(request)
        if not request.provider_config.model_name:
            return self._failure_response(
                request,
                "missing_model",
                "OpenAI frontier adapter requires FRONTIER_MODEL.",
            )
        if not request.provider_config.openai_api_key:
            return self._failure_response(
                request,
                "missing_api_key",
                "OpenAI frontier adapter requires OPENAI_API_KEY.",
            )
        try:
            client = self._build_client(
                request.provider_config.openai_api_key,
                request.provider_config.timeout_ms,
            )
            response = client.responses.create(**self._build_request_kwargs(request))
        except Exception as exc:
            return self._failure_response(
                request,
                "api_error",
                f"OpenAI frontier call failed: {exc}",
            )
        try:
            raw_response = self._coerce_raw_response(response)
            text_output = self._extract_text_output(response)
            parsed_output = json.loads(text_output)
        except Exception as exc:
            return FrontierJudgmentResponse(
                provider_name=self.provider_name,
                parsed_output={},
                raw_response=self._coerce_raw_response(response),
                provider_metadata={
                    "adapter_mode": "live_openai",
                    "model_name": request.provider_config.model_name,
                    "error_code": "malformed_json",
                    "error_message": f"OpenAI frontier response could not be parsed as JSON: {exc}",
                },
                status="failed",
            )
        return FrontierJudgmentResponse(
            provider_name=self.provider_name,
            parsed_output=parsed_output,
            raw_response=raw_response,
            provider_metadata={
                "adapter_mode": "live_openai",
                "model_name": request.provider_config.model_name,
                "response_id": self._safe_getattr(response, "id"),
            },
            status="success",
        )

    def _build_client(self, api_key: str, timeout_ms: int | None) -> Any:
        if self._client_factory is not None:
            return self._client_factory(api_key, timeout_ms)
        openai_module = importlib.import_module("openai")
        timeout_seconds = (timeout_ms / 1000) if timeout_ms is not None else None
        return openai_module.OpenAI(api_key=api_key, timeout=timeout_seconds)

    def _build_request_kwargs(self, request: FrontierJudgmentRequest) -> dict[str, Any]:
        prompt_payload = request.prompt_payload
        return {
            "model": request.provider_config.model_name,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt_payload["system_instructions"],
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(prompt_payload["user_payload"], sort_keys=True),
                        }
                    ],
                },
            ],
            "text": {"format": {"type": "json_object"}},
            "temperature": request.provider_config.temperature,
            "max_output_tokens": request.provider_config.max_output_tokens,
        }

    def _extract_text_output(self, response: Any) -> str:
        output_text = self._safe_getattr(response, "output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        if isinstance(response, dict):
            output_text = response.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text
        output_items = self._safe_getattr(response, "output")
        if output_items is None and isinstance(response, dict):
            output_items = response.get("output")
        if isinstance(output_items, list):
            for item in output_items:
                content_items = self._safe_getattr(item, "content")
                if content_items is None and isinstance(item, dict):
                    content_items = item.get("content")
                if not isinstance(content_items, list):
                    continue
                for content in content_items:
                    content_type = self._safe_getattr(content, "type")
                    if content_type is None and isinstance(content, dict):
                        content_type = content.get("type")
                    if content_type == "output_text":
                        text_value = self._safe_getattr(content, "text")
                        if text_value is None and isinstance(content, dict):
                            text_value = content.get("text")
                        if isinstance(text_value, str) and text_value.strip():
                            return text_value
        raise ValueError("No bounded JSON text output was returned by OpenAI.")

    def _coerce_raw_response(self, response: Any) -> dict | None:
        if isinstance(response, dict):
            return response
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if hasattr(response, "__dict__"):
            return dict(response.__dict__)
        return None

    def _failure_response(
        self,
        request: FrontierJudgmentRequest,
        error_code: str,
        error_message: str,
    ) -> FrontierJudgmentResponse:
        return FrontierJudgmentResponse(
            provider_name=self.provider_name,
            parsed_output={},
            raw_response=None,
            provider_metadata={
                "adapter_mode": "live_openai",
                "model_name": request.provider_config.model_name,
                "error_code": error_code,
                "error_message": error_message,
            },
            status="failed",
        )

    def _safe_getattr(self, value: Any, attr_name: str) -> Any:
        return getattr(value, attr_name, None)
