"""Stub frontier adapter for safe local testing."""

from __future__ import annotations

from invoice_exception_poc_a.frontier_adapters.base import FrontierAdapter
from invoice_exception_poc_a.frontier_adapters.model import (
    FrontierJudgmentRequest,
    FrontierJudgmentResponse,
)


class StubFrontierAdapter(FrontierAdapter):
    """Return a deterministic placeholder payload without calling any provider."""

    provider_name = "stub"

    def generate_judgment(self, request: FrontierJudgmentRequest) -> FrontierJudgmentResponse:
        case_id = request.normalized_case["case_id"]
        return FrontierJudgmentResponse(
            provider_name=self.provider_name,
            parsed_output={
                "case_id": case_id,
                "exception_type": "insufficient_information",
                "reason_summary": "Stub frontier adapter returned a placeholder bounded judgment.",
                "recommended_owner": "exception_review_queue",
                "priority": "low",
                "next_actions": ["Review the normalized case and replace the stub adapter with a live provider."],
                "questions_for_reviewer": ["What additional frontier prompt or provider wiring is still needed?"],
                "confidence": "low",
            },
            raw_response={
                "message": "stub_frontier_response",
                "prompt_payload_keys": sorted(request.prompt_payload.keys()),
            },
            provider_metadata={
                "adapter_mode": "stub",
                "model_name": request.provider_config.model_name,
            },
            status="success",
        )
