"""Factory helpers for frontier adapter selection."""

from __future__ import annotations

from invoice_exception_poc_a.frontier_adapters.base import FrontierAdapter
from invoice_exception_poc_a.frontier_adapters.openai_adapter import OpenAIFrontierAdapter
from invoice_exception_poc_a.frontier_adapters.stub import StubFrontierAdapter


def get_frontier_adapter(settings) -> FrontierAdapter:
    """Return the configured frontier adapter without wiring live inference here."""
    provider = settings.frontier.provider
    if provider == "stub":
        return StubFrontierAdapter()
    if provider == "openai":
        return OpenAIFrontierAdapter()
    raise ValueError(f"Unsupported frontier provider '{provider}'.")
