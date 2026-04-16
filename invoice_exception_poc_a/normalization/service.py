"""Canonical fact normalization for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.normalization.model import (
    InvoiceFacts,
    NormalizedCase,
    POFacts,
    PolicyFacts,
    UncertaintyItem,
    UncertaintySection,
    VendorFacts,
)


def normalize_case(case_envelope: dict) -> dict:
    """Return canonical normalized facts without adding reasoning."""
    invoice = case_envelope["invoice"]
    po_summary = case_envelope["po_summary"]
    vendor_master = case_envelope["vendor_master"]
    policy_rules = case_envelope["policy_rules"]
    prior_notes = case_envelope["prior_analyst_notes"]

    invoice_facts = InvoiceFacts(
        vendor_name=invoice.get("vendor_name"),
        invoice_number=invoice.get("invoice_number"),
        invoice_amount=invoice.get("invoice_amount"),
        payment_terms=invoice.get("payment_terms"),
        po_reference=invoice.get("po_reference") or po_summary.get("po_number"),
        tax=invoice.get("tax"),
        freight=invoice.get("freight"),
        supporting_notes=prior_notes.get("note_summary") if prior_notes else None,
    )
    po_facts = POFacts(
        po_number=po_summary.get("po_number"),
        expected_vendor=po_summary.get("expected_vendor") or vendor_master.get("vendor_name"),
        approved_total=po_summary.get("approved_total") or po_summary.get("po_amount"),
        payment_terms=po_summary.get("payment_terms") or vendor_master.get("payment_terms"),
        quantity_expectations=po_summary.get("quantity_expectations") or po_summary.get("line_summary"),
        comparison_anchors={
            "buyer_name": po_summary.get("buyer_name"),
            "line_summary": po_summary.get("line_summary"),
        },
    )
    vendor_facts = VendorFacts(
        canonical_vendor_name=vendor_master.get("vendor_name"),
        vendor_id=vendor_master.get("vendor_id"),
        standard_terms=vendor_master.get("payment_terms"),
        status_flags=[vendor_master["vendor_status"]] if vendor_master.get("vendor_status") else [],
        restrictions=vendor_master.get("restrictions") or [],
    )
    policy_facts = PolicyFacts(
        tolerance_thresholds={
            "percent": policy_rules.get("tolerance_threshold_percent"),
            "amount": policy_rules.get("tolerance_threshold_amount"),
        },
        routing_guidance=policy_rules.get("routing_guidance"),
        exception_rules=policy_rules.get("exception_rules") or [],
        review_instructions=policy_rules.get("review_instructions") or policy_rules.get("policy_anchor_reference"),
    )
    uncertainty = _build_uncertainty_section(
        invoice_facts=invoice_facts,
        po_facts=po_facts,
        vendor_facts=vendor_facts,
        policy_facts=policy_facts,
        receiving_summary=case_envelope["receiving_summary"],
    )

    normalized_case = NormalizedCase(
        case_id=case_envelope["metadata"]["case_id"],
        run_id=case_envelope["metadata"]["run_id"],
        run_started_at=case_envelope["metadata"]["run_started_at"],
        workflow_version=case_envelope["metadata"]["workflow_version"],
        prompt_version=case_envelope["metadata"]["prompt_version"],
        app_env=case_envelope["metadata"]["app_env"],
        source_payload=case_envelope["source_payload"],
        invoice_facts=invoice_facts,
        po_facts=po_facts,
        vendor_facts=vendor_facts,
        policy_facts=policy_facts,
        uncertainty=uncertainty,
        receiving_summary=case_envelope["receiving_summary"],
        contract_reference=case_envelope["contract_reference"],
        prior_analyst_notes=case_envelope["prior_analyst_notes"],
        upstream_exception_flags=case_envelope["upstream_exception_flags"],
    )
    return {
        "case_id": normalized_case.case_id,
        "run_id": normalized_case.run_id,
        "run_started_at": normalized_case.run_started_at,
        "workflow_version": normalized_case.workflow_version,
        "prompt_version": normalized_case.prompt_version,
        "app_env": normalized_case.app_env,
        "source_payload": normalized_case.source_payload,
        "invoice_facts": {
            "vendor_name": normalized_case.invoice_facts.vendor_name,
            "invoice_number": normalized_case.invoice_facts.invoice_number,
            "invoice_amount": normalized_case.invoice_facts.invoice_amount,
            "payment_terms": normalized_case.invoice_facts.payment_terms,
            "po_reference": normalized_case.invoice_facts.po_reference,
            "tax": normalized_case.invoice_facts.tax,
            "freight": normalized_case.invoice_facts.freight,
            "supporting_notes": normalized_case.invoice_facts.supporting_notes,
        },
        "po_facts": {
            "po_number": normalized_case.po_facts.po_number,
            "expected_vendor": normalized_case.po_facts.expected_vendor,
            "approved_total": normalized_case.po_facts.approved_total,
            "payment_terms": normalized_case.po_facts.payment_terms,
            "quantity_expectations": normalized_case.po_facts.quantity_expectations,
            "comparison_anchors": normalized_case.po_facts.comparison_anchors,
        },
        "vendor_facts": {
            "canonical_vendor_name": normalized_case.vendor_facts.canonical_vendor_name,
            "vendor_id": normalized_case.vendor_facts.vendor_id,
            "standard_terms": normalized_case.vendor_facts.standard_terms,
            "status_flags": normalized_case.vendor_facts.status_flags,
            "restrictions": normalized_case.vendor_facts.restrictions,
        },
        "policy_facts": {
            "tolerance_thresholds": normalized_case.policy_facts.tolerance_thresholds,
            "routing_guidance": normalized_case.policy_facts.routing_guidance,
            "exception_rules": normalized_case.policy_facts.exception_rules,
            "review_instructions": normalized_case.policy_facts.review_instructions,
        },
        "uncertainty": {
            "missing_information": [
                {"code": item.code, "message": item.message, "fields": item.fields}
                for item in normalized_case.uncertainty.missing_information
            ],
            "conflicting_information": [
                {"code": item.code, "message": item.message, "fields": item.fields}
                for item in normalized_case.uncertainty.conflicting_information
            ],
            "uncertainty_flags": normalized_case.uncertainty.uncertainty_flags,
        },
        "receiving_summary": normalized_case.receiving_summary,
        "contract_reference": normalized_case.contract_reference,
        "prior_analyst_notes": normalized_case.prior_analyst_notes,
        "upstream_exception_flags": normalized_case.upstream_exception_flags,
    }


def _build_uncertainty_section(
    *,
    invoice_facts: InvoiceFacts,
    po_facts: POFacts,
    vendor_facts: VendorFacts,
    policy_facts: PolicyFacts,
    receiving_summary: dict | None,
) -> UncertaintySection:
    """Build deterministic missing/conflicting information signals."""
    missing_information: list[UncertaintyItem] = []
    conflicting_information: list[UncertaintyItem] = []

    if not invoice_facts.po_reference:
        missing_information.append(
            UncertaintyItem(
                code="missing_po_reference",
                message="PO reference is not available on the invoice or PO context.",
                fields=["invoice_facts.po_reference", "po_facts.po_number"],
            )
        )
    if not invoice_facts.invoice_number:
        missing_information.append(
            UncertaintyItem(
                code="missing_invoice_number",
                message="Invoice number is missing from invoice facts.",
                fields=["invoice_facts.invoice_number"],
            )
        )
    if invoice_facts.invoice_amount is None:
        missing_information.append(
            UncertaintyItem(
                code="missing_invoice_amount",
                message="Invoice amount is missing from invoice facts.",
                fields=["invoice_facts.invoice_amount"],
            )
        )
    if not vendor_facts.vendor_id or not vendor_facts.canonical_vendor_name:
        missing_information.append(
            UncertaintyItem(
                code="missing_vendor_identity",
                message="Vendor identity is incomplete because vendor ID or canonical vendor name is missing.",
                fields=["vendor_facts.vendor_id", "vendor_facts.canonical_vendor_name"],
            )
        )
    if (
        policy_facts.tolerance_thresholds.get("percent") is None
        and policy_facts.tolerance_thresholds.get("amount") is None
    ):
        missing_information.append(
            UncertaintyItem(
                code="missing_policy_thresholds",
                message="Policy tolerance thresholds are missing.",
                fields=["policy_facts.tolerance_thresholds.percent", "policy_facts.tolerance_thresholds.amount"],
            )
        )
    if not policy_facts.routing_guidance:
        missing_information.append(
            UncertaintyItem(
                code="missing_routing_guidance",
                message="Policy routing guidance is missing.",
                fields=["policy_facts.routing_guidance"],
            )
        )
    if po_facts.quantity_expectations and receiving_summary is None:
        missing_information.append(
            UncertaintyItem(
                code="missing_receiving_summary",
                message="Receiving summary is absent even though PO quantity expectations are present.",
                fields=["receiving_summary", "po_facts.quantity_expectations"],
            )
        )

    if (
        invoice_facts.vendor_name
        and po_facts.expected_vendor
        and invoice_facts.vendor_name != po_facts.expected_vendor
    ):
        conflicting_information.append(
            UncertaintyItem(
                code="vendor_name_mismatch",
                message="Invoice vendor name does not match the expected vendor from PO or vendor master.",
                fields=["invoice_facts.vendor_name", "po_facts.expected_vendor"],
            )
        )
    if (
        invoice_facts.po_reference
        and po_facts.po_number
        and invoice_facts.po_reference != po_facts.po_number
    ):
        conflicting_information.append(
            UncertaintyItem(
                code="po_reference_conflict",
                message="Invoice PO reference conflicts with the PO number in PO facts.",
                fields=["invoice_facts.po_reference", "po_facts.po_number"],
            )
        )
    if (
        invoice_facts.payment_terms
        and po_facts.payment_terms
        and invoice_facts.payment_terms != po_facts.payment_terms
    ):
        conflicting_information.append(
            UncertaintyItem(
                code="payment_terms_conflict",
                message="Invoice payment terms conflict with PO or vendor standard terms.",
                fields=["invoice_facts.payment_terms", "po_facts.payment_terms", "vendor_facts.standard_terms"],
            )
        )
    if (
        invoice_facts.invoice_amount is not None
        and po_facts.approved_total is not None
        and invoice_facts.invoice_amount > po_facts.approved_total
    ):
        conflicting_information.append(
            UncertaintyItem(
                code="invoice_amount_exceeds_po_total",
                message="Invoice amount exceeds the approved PO total.",
                fields=["invoice_facts.invoice_amount", "po_facts.approved_total"],
            )
        )

    uncertainty_flags: list[str] = []
    if missing_information:
        uncertainty_flags.append("missing_information_present")
    if conflicting_information:
        uncertainty_flags.append("conflicting_information_present")

    return UncertaintySection(
        missing_information=missing_information,
        conflicting_information=conflicting_information,
        uncertainty_flags=uncertainty_flags,
    )
