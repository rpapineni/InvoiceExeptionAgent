"""OpenAI adapter seam for later frontier integration."""

from __future__ import annotations

from collections.abc import Callable

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
    ) -> None:
        self._response_transport = response_transport

    def generate_judgment(self, request: FrontierJudgmentRequest) -> FrontierJudgmentResponse:
        """Use an injected transport for tests, or return a bounded skeleton response."""
        if self._response_transport is not None:
            return self._response_transport(request)
        return FrontierJudgmentResponse(
            provider_name=self.provider_name,
            parsed_output={},
            raw_response=None,
            provider_metadata={
                "adapter_mode": "skeleton",
                "model_name": request.provider_config.model_name,
                "integration_status": "not_wired",
            },
            status="not_implemented",
        )
