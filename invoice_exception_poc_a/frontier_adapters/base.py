"""Base interface for frontier providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from invoice_exception_poc_a.frontier_adapters.model import (
    FrontierJudgmentRequest,
    FrontierJudgmentResponse,
)


class FrontierAdapter(ABC):
    """Provider-agnostic interface for bounded frontier judgment generation."""

    provider_name: str

    @abstractmethod
    def generate_judgment(self, request: FrontierJudgmentRequest) -> FrontierJudgmentResponse:
        """Return one bounded frontier judgment response for a normalized case."""
