"""Typed request and response structures for bounded frontier judgments."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FrontierProviderConfig:
    """Provider-neutral runtime configuration for one frontier adapter call."""

    provider_name: str
    model_name: str | None = None
    timeout_ms: int | None = None
    max_retries: int = 0
    temperature: float = 0.0
    max_output_tokens: int | None = None
    openai_api_key: str | None = None
    extra_options: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FrontierJudgmentRequest:
    """Bounded frontier input payload assembled outside provider code."""

    normalized_case: dict
    uncertainty_section: dict
    prompt_payload: dict
    provider_config: FrontierProviderConfig


@dataclass(frozen=True)
class FrontierJudgmentResponse:
    """Bounded provider response payload for later parsing or evaluation."""

    provider_name: str
    parsed_output: dict
    raw_response: dict | None = None
    provider_metadata: dict = field(default_factory=dict)
    status: str = "success"
