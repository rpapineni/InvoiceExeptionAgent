"""Provider-agnostic frontier adapter layer for PoC A-F."""

from invoice_exception_poc_a.frontier_adapters.base import FrontierAdapter
from invoice_exception_poc_a.frontier_adapters.factory import get_frontier_adapter
from invoice_exception_poc_a.frontier_adapters.model import (
    FrontierJudgmentRequest,
    FrontierJudgmentResponse,
    FrontierProviderConfig,
)
from invoice_exception_poc_a.frontier_adapters.openai_adapter import OpenAIFrontierAdapter
from invoice_exception_poc_a.frontier_adapters.stub import StubFrontierAdapter

__all__ = [
    "FrontierAdapter",
    "FrontierJudgmentRequest",
    "FrontierJudgmentResponse",
    "FrontierProviderConfig",
    "get_frontier_adapter",
    "OpenAIFrontierAdapter",
    "StubFrontierAdapter",
]
