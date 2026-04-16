"""Bounded classification result structures for PoC A triage."""

from __future__ import annotations

from dataclasses import dataclass


EXCEPTION_TAXONOMY = (
    "amount_mismatch",
    "missing_po",
    "vendor_mismatch",
    "terms_mismatch",
    "duplicate_invoice_suspected",
    "receiving_mismatch",
    "policy_tolerance_breach",
    "insufficient_information",
)

CONFIDENCE_SCALE = ("high", "medium", "low")
OWNER_CATEGORIES = (
    "ap_analyst",
    "buyer_procurement",
    "receiving_operations",
    "vendor_management",
    "finance_controller",
    "exception_review_queue",
)
PRIORITY_SCALE = ("low", "medium", "high")


@dataclass(frozen=True)
class ClassificationResult:
    """Single bounded first-pass classification result for one normalized case."""

    exception_type: str
    confidence: str


@dataclass(frozen=True)
class RecommendationResult:
    """Single bounded owner and priority recommendation for one classified case."""

    recommended_owner: str
    priority: str


@dataclass(frozen=True)
class ReviewerGuidanceResult:
    """Bounded reviewer guidance for the current classified case."""

    next_actions: list[str]
    questions_for_reviewer: list[str]
