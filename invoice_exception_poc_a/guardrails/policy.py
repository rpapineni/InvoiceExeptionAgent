"""Explicit PoC A scope guardrails."""

from __future__ import annotations

from dataclasses import dataclass


UNSUPPORTED_CAPABILITIES = (
    "prior_case_retrieval",
    "feedback_reuse",
    "autonomous_routing",
    "approve_action",
    "reject_action",
    "pay_action",
    "outbound_communication",
    "cross_case_memory",
)


@dataclass(frozen=True)
class ScopeGuardrailError(Exception):
    """Raised when out-of-scope capability is requested in PoC A."""

    capability: str

    def __str__(self) -> str:
        return (
            f"Capability '{self.capability}' is unsupported in PoC A. "
            "PoC A is bounded to stateless first-pass triage for analyst review only."
        )


def get_guardrails_snapshot() -> dict:
    """Return the explicit PoC A boundary definition."""
    return {
        "poc": "A",
        "stateless_across_cases": True,
        "downstream_actions_enabled": False,
        "feedback_persistence_enabled": False,
        "prior_case_retrieval_enabled": False,
        "unsupported_capabilities": list(UNSUPPORTED_CAPABILITIES),
    }


def assert_capability_supported(capability: str) -> None:
    """Block unsupported capabilities explicitly rather than leaving ambiguity."""
    if capability in UNSUPPORTED_CAPABILITIES:
        raise ScopeGuardrailError(capability)
