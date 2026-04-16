"""Deterministic reviewer guidance generation for bounded PoC A triage."""

from __future__ import annotations

from invoice_exception_poc_a.triage.model import ReviewerGuidanceResult


def generate_reviewer_guidance(classification: dict, normalized_case: dict, recommendation: dict) -> dict:
    """Return concrete next actions and reviewer questions for the case."""
    exception_type = classification["exception_type"]
    owner = recommendation["recommended_owner"]
    uncertainty = normalized_case["uncertainty"]

    next_actions = _next_actions_for(exception_type, owner)
    questions = _questions_for(exception_type, normalized_case, uncertainty)
    result = ReviewerGuidanceResult(next_actions=next_actions, questions_for_reviewer=questions)
    return {
        "next_actions": result.next_actions,
        "questions_for_reviewer": result.questions_for_reviewer,
    }


def _next_actions_for(exception_type: str, owner: str) -> list[str]:
    """Build bounded next actions by exception type."""
    owner_phrase = owner.replace("_", " ")
    if exception_type == "missing_po":
        return [
            "Verify whether a valid PO exists for this invoice.",
            "Confirm whether the invoice was expected to be processed as a non-PO invoice.",
            f"Prepare the case for review by {owner_phrase} if a PO-backed path is confirmed.",
        ]
    if exception_type == "vendor_mismatch":
        return [
            "Compare the invoicing entity to the supplier listed on the PO and vendor master.",
            "Check whether supplier onboarding or vendor master data needs correction.",
            f"Prepare the mismatch details for review by {owner_phrase}.",
        ]
    if exception_type == "terms_mismatch":
        return [
            "Compare invoice payment terms to the PO terms and vendor standard terms.",
            "Check whether a contract or approved exception supports the invoice terms.",
            f"Document the terms variance for review by {owner_phrase}.",
        ]
    if exception_type == "amount_mismatch":
        return [
            "Compare the invoice amount to the approved PO amount and relevant line values.",
            "Check whether an approved adjustment or change order explains the variance.",
            f"Prepare the amount comparison for review by {owner_phrase}.",
        ]
    if exception_type == "policy_tolerance_breach":
        return [
            "Verify the amount variance against configured policy thresholds.",
            "Check whether an exception approval exists for the over-tolerance amount.",
            f"Prepare the variance details for review by {owner_phrase} without routing automatically.",
        ]
    if exception_type == "receiving_mismatch":
        return [
            "Review receipt status and any receiving documents tied to the PO.",
            "Confirm whether goods or services were fully received before invoice matching.",
            f"Prepare the receiving discrepancy for review by {owner_phrase}.",
        ]
    if exception_type == "duplicate_invoice_suspected":
        return [
            "Compare invoice identifiers and amounts against possible prior submissions.",
            "Check whether the document is a resubmission, rebill, or true duplicate.",
            f"Prepare the duplicate-review evidence for {owner_phrase}.",
        ]
    return [
        "Gather the core case anchors needed for invoice, PO, vendor, and policy comparison.",
        "Confirm which key fields are missing before further triage is attempted.",
        f"Prepare the incomplete case for review by {owner_phrase}.",
    ]


def _questions_for(exception_type: str, normalized_case: dict, uncertainty: dict) -> list[str]:
    """Build reviewer questions grounded in the actual uncertainty signals."""
    missing_codes = {item["code"] for item in uncertainty["missing_information"]}
    conflict_codes = {item["code"] for item in uncertainty["conflicting_information"]}
    invoice_facts = normalized_case["invoice_facts"]
    po_facts = normalized_case["po_facts"]

    questions: list[str] = []
    if exception_type == "missing_po":
        questions.extend(
            [
                "Is there a valid PO number for this invoice?",
                "Was this invoice expected to be processed as a non-PO invoice?",
            ]
        )
    elif exception_type == "vendor_mismatch":
        questions.extend(
            [
                "Is the invoicing entity the same as the approved supplier?",
                "Does vendor master data need to be updated for this supplier relationship?",
            ]
        )
    elif exception_type == "terms_mismatch":
        questions.extend(
            [
                "Are the invoice payment terms contractually approved?",
                "Should the PO terms or vendor standard terms govern this invoice?",
            ]
        )
    elif exception_type == "amount_mismatch":
        questions.extend(
            [
                "Is the amount difference expected for this invoice?",
                "Was there a change order or approved adjustment that explains the variance?",
            ]
        )
    elif exception_type == "policy_tolerance_breach":
        questions.extend(
            [
                "Was an exception approval granted for this variance?",
                "Does policy permit this level of difference from the approved amount?",
            ]
        )
    elif exception_type == "receiving_mismatch":
        questions.extend(
            [
                "Were the goods or services fully received for this invoice?",
                "Is receiving data missing or inconsistent with the PO expectations?",
            ]
        )
    elif exception_type == "duplicate_invoice_suspected":
        questions.extend(
            [
                "Is this document a resubmission, credit-rebill, or true duplicate?",
                "Do repeated invoice identifiers point to a duplicate processing risk?",
            ]
        )
    else:
        questions.extend(
            [
                "What key fields are missing that block stronger triage?",
                "Which core anchors need to be collected before the case can move forward?",
            ]
        )

    if "missing_vendor_identity" in missing_codes:
        questions.append("Can vendor identity be confirmed from the latest vendor master or supplier record?")
    if "missing_invoice_amount" in missing_codes:
        questions.append("Can the invoice amount be confirmed from the source document?")
    if "missing_po_reference" in missing_codes and exception_type != "missing_po":
        questions.append("Can the correct PO reference be located for this invoice?")
    if "vendor_name_mismatch" in conflict_codes and exception_type != "vendor_mismatch":
        questions.append(
            f"Should invoice vendor '{invoice_facts.get('vendor_name')}' or expected vendor '{po_facts.get('expected_vendor')}' be treated as authoritative?"
        )
    if "payment_terms_conflict" in conflict_codes and exception_type != "terms_mismatch":
        questions.append("Which payment terms should govern this case after review of PO and vendor records?")

    # Keep guidance concise and predictable.
    unique_questions: list[str] = []
    for question in questions:
        if question not in unique_questions:
            unique_questions.append(question)
    return unique_questions[:4]
