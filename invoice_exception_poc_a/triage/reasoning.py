"""Business-readable reason summary generation for bounded PoC A triage."""

from __future__ import annotations


def generate_reason_summary(classification: dict, normalized_case: dict) -> str:
    """Generate a concise fact-grounded summary for the selected exception type."""
    exception_type = classification["exception_type"]
    confidence = classification["confidence"]
    invoice_facts = normalized_case["invoice_facts"]
    po_facts = normalized_case["po_facts"]
    vendor_facts = normalized_case["vendor_facts"]
    policy_facts = normalized_case["policy_facts"]
    uncertainty = normalized_case["uncertainty"]

    missing_codes = {item["code"] for item in uncertainty["missing_information"]}
    caution = (
        " Confidence is limited because some core information is missing or conflicting."
        if confidence == "low"
        else ""
    )

    if exception_type == "missing_po":
        return (
            "The case appears to be a missing PO issue because the invoice does not have a usable PO reference "
            "and the PO anchor needed for comparison is not available." + caution
        )
    if exception_type == "vendor_mismatch":
        return (
            f"The invoice vendor '{invoice_facts.get('vendor_name')}' does not align with the expected vendor "
            f"'{po_facts.get('expected_vendor')}', so the case is best treated as a vendor mismatch." + caution
        )
    if exception_type == "terms_mismatch":
        return (
            f"The invoice payment terms '{invoice_facts.get('payment_terms')}' differ from the PO or vendor standard "
            f"terms '{po_facts.get('payment_terms')}', indicating a terms mismatch." + caution
        )
    if exception_type == "amount_mismatch":
        return (
            f"The invoice amount of {invoice_facts.get('invoice_amount')} does not align with the approved PO total "
            f"of {po_facts.get('approved_total')}, so the case is best treated as an amount mismatch." + caution
        )
    if exception_type == "policy_tolerance_breach":
        thresholds = policy_facts.get("tolerance_thresholds", {})
        return (
            f"The invoice amount of {invoice_facts.get('invoice_amount')} exceeds the approved PO total of "
            f"{po_facts.get('approved_total')} by more than the configured tolerance thresholds "
            f"(amount={thresholds.get('amount')}, percent={thresholds.get('percent')}), so this appears to be a "
            "policy tolerance breach." + caution
        )
    if exception_type == "receiving_mismatch":
        receipt_status = (normalized_case.get("receiving_summary") or {}).get("receipt_status")
        return (
            f"Receiving context shows status '{receipt_status}' while the PO still carries quantity expectations, "
            "so the case is best treated as a receiving mismatch." + caution
        )
    if exception_type == "duplicate_invoice_suspected":
        flags = (normalized_case.get("upstream_exception_flags") or {}).get("flags") or []
        return (
            f"Upstream exception signals include {', '.join(flags)}, so the case should be treated as a suspected "
            "duplicate invoice pending analyst review." + caution
        )
    if exception_type == "insufficient_information":
        missing_labels = []
        if "missing_invoice_number" in missing_codes:
            missing_labels.append("invoice number")
        if "missing_invoice_amount" in missing_codes:
            missing_labels.append("invoice amount")
        if "missing_vendor_identity" in missing_codes:
            missing_labels.append("vendor identity")
        if "missing_policy_thresholds" in missing_codes:
            missing_labels.append("policy thresholds")
        if "missing_routing_guidance" in missing_codes:
            missing_labels.append("routing guidance")
        if not missing_labels:
            missing_labels.append("core comparison anchors")
        return (
            "The case does not have enough core information to support a stronger first-pass classification because "
            f"{', '.join(missing_labels)} are missing."
        )

    return "The case was classified using bounded first-pass rules, but the supporting summary is unavailable."
