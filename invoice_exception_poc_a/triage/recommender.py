"""Deterministic owner and priority recommendation for bounded PoC A triage."""

from __future__ import annotations

from invoice_exception_poc_a.triage.model import RecommendationResult


DEFAULT_OWNER_BY_EXCEPTION = {
    "missing_po": "buyer_procurement",
    "vendor_mismatch": "vendor_management",
    "terms_mismatch": "ap_analyst",
    "receiving_mismatch": "receiving_operations",
    "policy_tolerance_breach": "finance_controller",
    "amount_mismatch": "ap_analyst",
    "duplicate_invoice_suspected": "ap_analyst",
    "insufficient_information": "exception_review_queue",
}


def recommend_owner_and_priority(classification: dict, normalized_case: dict) -> dict:
    """Return exactly one bounded owner and priority recommendation."""
    owner = _determine_owner(classification["exception_type"], normalized_case)
    priority = _determine_priority(classification, normalized_case)
    result = RecommendationResult(recommended_owner=owner, priority=priority)
    return {
        "recommended_owner": result.recommended_owner,
        "priority": result.priority,
    }


def _determine_owner(exception_type: str, normalized_case: dict) -> str:
    """Choose one owner using exception type first, then policy guidance influence."""
    default_owner = DEFAULT_OWNER_BY_EXCEPTION.get(exception_type, "exception_review_queue")
    routing_guidance = (normalized_case.get("policy_facts") or {}).get("routing_guidance") or ""
    guidance = routing_guidance.lower()

    # Keep default category mappings stable for strongly-typed cases; let policy guidance
    # influence broad/default paths instead of overriding every category.
    if default_owner not in {"ap_analyst", "exception_review_queue"}:
        return default_owner

    if "finance controller" in guidance or "controller" in guidance:
        return "finance_controller"
    if "receiving" in guidance:
        return "receiving_operations"
    if "vendor" in guidance:
        return "vendor_management"
    if "buyer" in guidance or "procurement" in guidance:
        return "buyer_procurement"
    if "ap analyst" in guidance or "ap review" in guidance or "analyst review" in guidance:
        return "ap_analyst"
    if "review queue" in guidance or "exception queue" in guidance:
        return "exception_review_queue"
    return default_owner


def _determine_priority(classification: dict, normalized_case: dict) -> str:
    """Choose one bounded priority from severity and uncertainty signals."""
    exception_type = classification["exception_type"]
    confidence = classification["confidence"]
    invoice_amount = normalized_case["invoice_facts"].get("invoice_amount")
    approved_total = normalized_case["po_facts"].get("approved_total")
    conflicting_count = len(normalized_case["uncertainty"]["conflicting_information"])
    missing_count = len(normalized_case["uncertainty"]["missing_information"])

    if exception_type == "policy_tolerance_breach":
        return "high"
    if exception_type == "insufficient_information":
        return "medium"
    if exception_type == "receiving_mismatch":
        return "medium"
    if exception_type == "duplicate_invoice_suspected":
        return "high"
    if (
        exception_type == "amount_mismatch"
        and invoice_amount is not None
        and approved_total is not None
        and invoice_amount > approved_total
    ):
        if invoice_amount - approved_total >= 100:
            return "high"
        return "medium"
    if confidence == "low" and (missing_count > 0 or conflicting_count > 1):
        return "medium"
    return "low"
