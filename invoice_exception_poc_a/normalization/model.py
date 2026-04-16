"""Canonical normalized case structures for PoC A."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceFacts:
    """Canonical invoice facts for downstream triage."""

    vendor_name: str | None
    invoice_number: str | None
    invoice_amount: float | None
    payment_terms: str | None
    po_reference: str | None
    tax: float | None
    freight: float | None
    supporting_notes: str | None


@dataclass(frozen=True)
class POFacts:
    """Canonical purchase-order facts for downstream triage."""

    po_number: str | None
    expected_vendor: str | None
    approved_total: float | None
    payment_terms: str | None
    quantity_expectations: str | None
    comparison_anchors: dict


@dataclass(frozen=True)
class VendorFacts:
    """Canonical vendor-master facts for downstream triage."""

    canonical_vendor_name: str | None
    vendor_id: str | None
    standard_terms: str | None
    status_flags: list[str]
    restrictions: list[str]


@dataclass(frozen=True)
class PolicyFacts:
    """Canonical policy facts for downstream triage."""

    tolerance_thresholds: dict
    routing_guidance: str | None
    exception_rules: list[str]
    review_instructions: str | None


@dataclass(frozen=True)
class UncertaintyItem:
    """Structured missing or conflicting information for downstream explanation."""

    code: str
    message: str
    fields: list[str]


@dataclass(frozen=True)
class UncertaintySection:
    """Structured uncertainty signals for the normalized case."""

    missing_information: list[UncertaintyItem]
    conflicting_information: list[UncertaintyItem]
    uncertainty_flags: list[str]


@dataclass(frozen=True)
class NormalizedCase:
    """Normalized PoC A case with canonical facts and explicit null handling."""

    case_id: str
    run_id: str
    run_started_at: str
    workflow_version: str
    prompt_version: str
    app_env: str
    source_payload: dict
    invoice_facts: InvoiceFacts
    po_facts: POFacts
    vendor_facts: VendorFacts
    policy_facts: PolicyFacts
    uncertainty: UncertaintySection
    receiving_summary: dict | None
    contract_reference: dict | None
    prior_analyst_notes: dict | None
    upstream_exception_flags: dict | None
