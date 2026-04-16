"""Deterministic first-pass exception classification for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.triage.model import ClassificationResult


PRECEDENCE_ORDER = (
    "missing_po",
    "duplicate_invoice_suspected",
    "vendor_mismatch",
    "terms_mismatch",
    "receiving_mismatch",
    "policy_tolerance_breach",
    "amount_mismatch",
    "insufficient_information",
)


def classify_primary_exception(normalized_case: dict) -> dict:
    """Return exactly one primary exception type and bounded confidence."""
    candidates = _detect_candidates(normalized_case)
    selected = next((label for label in PRECEDENCE_ORDER if label in candidates), "insufficient_information")
    confidence = _assign_confidence(selected, normalized_case)
    result = ClassificationResult(exception_type=selected, confidence=confidence)
    return {
        "exception_type": result.exception_type,
        "confidence": result.confidence,
        "precedence_order": list(PRECEDENCE_ORDER),
    }


def _detect_candidates(normalized_case: dict) -> set[str]:
    """Collect all triggered categories before precedence selects one."""
    candidates: set[str] = set()
    missing_codes = {item["code"] for item in normalized_case["uncertainty"]["missing_information"]}
    conflict_codes = {item["code"] for item in normalized_case["uncertainty"]["conflicting_information"]}
    invoice_facts = normalized_case["invoice_facts"]
    po_facts = normalized_case["po_facts"]
    policy_facts = normalized_case["policy_facts"]
    receiving_summary = normalized_case["receiving_summary"]
    upstream_flags = normalized_case["upstream_exception_flags"] or {}
    flags = set(upstream_flags.get("flags") or [])

    if "missing_po_reference" in missing_codes:
        candidates.add("missing_po")
    if "vendor_name_mismatch" in conflict_codes:
        candidates.add("vendor_mismatch")
    if "payment_terms_conflict" in conflict_codes:
        candidates.add("terms_mismatch")
    if "duplicate_invoice_suspected" in flags or "duplicate_invoice" in flags:
        candidates.add("duplicate_invoice_suspected")
    if (
        receiving_summary
        and receiving_summary.get("receipt_status") in {"NO_RECEIPT", "PARTIAL_RECEIPT", "MISMATCH"}
        and po_facts.get("quantity_expectations")
    ):
        candidates.add("receiving_mismatch")

    invoice_amount = invoice_facts.get("invoice_amount")
    approved_total = po_facts.get("approved_total")
    threshold_amount = policy_facts["tolerance_thresholds"].get("amount")
    threshold_percent = policy_facts["tolerance_thresholds"].get("percent")
    if invoice_amount is not None and approved_total is not None and invoice_amount > approved_total:
        overage = invoice_amount - approved_total
        percent_over = (overage / approved_total * 100) if approved_total else None
        if (
            threshold_amount is not None
            and overage > threshold_amount
            or threshold_percent is not None
            and percent_over is not None
            and percent_over > threshold_percent
        ):
            candidates.add("policy_tolerance_breach")
        else:
            candidates.add("amount_mismatch")

    critical_missing = {
        "missing_invoice_number",
        "missing_invoice_amount",
        "missing_vendor_identity",
        "missing_policy_thresholds",
        "missing_routing_guidance",
    }
    if not candidates and missing_codes.intersection(critical_missing):
        candidates.add("insufficient_information")

    if not candidates:
        candidates.add("insufficient_information")

    return candidates


def _assign_confidence(exception_type: str, normalized_case: dict) -> str:
    """Assign bounded confidence from signal clarity and uncertainty volume."""
    missing_count = len(normalized_case["uncertainty"]["missing_information"])
    conflict_count = len(normalized_case["uncertainty"]["conflicting_information"])

    if exception_type == "insufficient_information":
        return "low"
    if missing_count == 0 and conflict_count <= 1:
        return "high"
    if missing_count <= 1 and conflict_count <= 1:
        return "medium"
    return "low"
