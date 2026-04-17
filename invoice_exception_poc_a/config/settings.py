"""Environment-driven settings for the PoC A scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass


ALLOWED_TRIAGE_ENGINES = ("deterministic", "frontier")
ALLOWED_FRONTIER_PROVIDERS = ("openai", "stub")
DEFAULT_FRONTIER_TIMEOUT_MS = 30000
DEFAULT_FRONTIER_MAX_RETRIES = 0
DEFAULT_FRONTIER_TEMPERATURE = 0.0
DEFAULT_FRONTIER_MAX_OUTPUT_TOKENS = 512


@dataclass(frozen=True)
class FrontierSettings:
    """Externalized provider-neutral runtime settings for the frontier adapter layer."""

    provider: str | None = None
    model: str | None = None
    timeout_ms: int = DEFAULT_FRONTIER_TIMEOUT_MS
    max_retries: int = DEFAULT_FRONTIER_MAX_RETRIES
    temperature: float = DEFAULT_FRONTIER_TEMPERATURE
    max_output_tokens: int = DEFAULT_FRONTIER_MAX_OUTPUT_TOKENS
    openai_api_key: str | None = None


@dataclass(frozen=True)
class Settings:
    workflow_version: str = "0.1.0"
    prompt_version: str = "placeholder-prompt-v1"
    app_env: str = "local"
    triage_engine: str = "deterministic"
    frontier: FrontierSettings = FrontierSettings()


def get_settings() -> Settings:
    """Load externally configurable version identifiers."""
    triage_engine = os.getenv("TRIAGE_ENGINE", "deterministic")
    if triage_engine not in ALLOWED_TRIAGE_ENGINES:
        allowed = ", ".join(ALLOWED_TRIAGE_ENGINES)
        raise ValueError(f"Invalid TRIAGE_ENGINE '{triage_engine}'. Allowed values: {allowed}.")
    frontier = FrontierSettings(
        provider=os.getenv("FRONTIER_PROVIDER"),
        model=os.getenv("FRONTIER_MODEL"),
        timeout_ms=_get_int_env("FRONTIER_TIMEOUT_MS", DEFAULT_FRONTIER_TIMEOUT_MS),
        max_retries=_get_int_env("FRONTIER_MAX_RETRIES", DEFAULT_FRONTIER_MAX_RETRIES),
        temperature=_get_float_env("FRONTIER_TEMPERATURE", DEFAULT_FRONTIER_TEMPERATURE),
        max_output_tokens=_get_int_env("FRONTIER_MAX_OUTPUT_TOKENS", DEFAULT_FRONTIER_MAX_OUTPUT_TOKENS),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    if triage_engine == "frontier":
        _validate_frontier_settings(frontier)
    return Settings(
        workflow_version=os.getenv("WORKFLOW_VERSION", "0.1.0"),
        prompt_version=os.getenv("PROMPT_VERSION", "placeholder-prompt-v1"),
        app_env=os.getenv("APP_ENV", "local"),
        triage_engine=triage_engine,
        frontier=frontier,
    )


def _validate_frontier_settings(frontier: FrontierSettings) -> None:
    if not frontier.provider:
        raise ValueError("FRONTIER_PROVIDER is required when TRIAGE_ENGINE=frontier.")
    if frontier.provider not in ALLOWED_FRONTIER_PROVIDERS:
        allowed = ", ".join(ALLOWED_FRONTIER_PROVIDERS)
        raise ValueError(
            f"Invalid FRONTIER_PROVIDER '{frontier.provider}'. Allowed values: {allowed}."
        )
    if not frontier.model:
        raise ValueError("FRONTIER_MODEL is required when TRIAGE_ENGINE=frontier.")
    if frontier.timeout_ms < 1:
        raise ValueError("FRONTIER_TIMEOUT_MS must be greater than 0.")
    if frontier.max_retries < 0:
        raise ValueError("FRONTIER_MAX_RETRIES must be greater than or equal to 0.")
    if frontier.max_output_tokens < 1:
        raise ValueError("FRONTIER_MAX_OUTPUT_TOKENS must be greater than 0.")


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc
