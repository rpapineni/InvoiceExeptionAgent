"""Formal input contract for one PoC A invoice exception case.

This module defines the required and optional sections accepted by PoC A.
The contract is limited to shape validation for a single case payload and
does not perform reasoning, normalization, or downstream workflow logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceSection:
    """Required invoice context including identity, vendor name, amount, and terms."""

    invoice_number: str
    vendor_name: str
    invoice_amount: float
    currency: str
    payment_terms: str


@dataclass(frozen=True)
class POSummarySection:
    """Required PO context including PO reference and line summary anchor."""

    po_number: str
    buyer_name: str
    po_amount: float
    currency: str
    line_summary: str


@dataclass(frozen=True)
class VendorMasterSection:
    """Required vendor master context including vendor identity and payment setup."""

    vendor_id: str
    vendor_name: str
    payment_terms: str
    payment_method: str
    vendor_status: str


@dataclass(frozen=True)
class PolicyRulesSection:
    """Required policy context including tolerances and routing guidance anchors."""

    tolerance_threshold_percent: float
    tolerance_threshold_amount: float
    routing_guidance: str
    policy_anchor_reference: str


@dataclass(frozen=True)
class ReceivingSummarySection:
    """Optional receiving context summarizing receipt status for the case."""

    receipt_status: str
    received_amount: float
    receipt_reference: str


@dataclass(frozen=True)
class ContractReferenceSection:
    """Optional contract anchor information related to the invoice or PO."""

    contract_id: str
    contract_title: str
    contract_anchor_reference: str


@dataclass(frozen=True)
class PriorAnalystNotesSection:
    """Optional human-authored notes included as case context only."""

    note_summary: str
    note_reference: str


@dataclass(frozen=True)
class UpstreamExceptionFlagsSection:
    """Optional upstream flags that identify pre-existing exception markers."""

    source_system: str
    flags: list[str]


@dataclass(frozen=True)
class CaseInputContract:
    """Formal contract for one invoice exception case in PoC A.

    Required top-level sections:
    - case_id: unique case identifier
    - invoice: invoice details from text or structured extraction
    - po_summary: PO reference summary for analyst review
    - vendor_master: vendor master reference fields
    - policy_rules: policy/tolerance guidance anchors

    Optional top-level sections:
    - receiving_summary
    - contract_reference
    - prior_analyst_notes
    - upstream_exception_flags
    """

    case_id: str
    invoice: InvoiceSection
    po_summary: POSummarySection
    vendor_master: VendorMasterSection
    policy_rules: PolicyRulesSection
    receiving_summary: ReceivingSummarySection | None = None
    contract_reference: ContractReferenceSection | None = None
    prior_analyst_notes: PriorAnalystNotesSection | None = None
    upstream_exception_flags: UpstreamExceptionFlagsSection | None = None


REQUIRED_TOP_LEVEL_FIELDS = (
    "case_id",
    "invoice",
    "po_summary",
    "vendor_master",
    "policy_rules",
)

OPTIONAL_TOP_LEVEL_FIELDS = (
    "receiving_summary",
    "contract_reference",
    "prior_analyst_notes",
    "upstream_exception_flags",
)

SECTION_FIELD_RULES = {
    "invoice": ("invoice_number", "vendor_name", "invoice_amount", "currency", "payment_terms"),
    "po_summary": ("po_number", "buyer_name", "po_amount", "currency", "line_summary"),
    "vendor_master": ("vendor_id", "vendor_name", "payment_terms", "payment_method", "vendor_status"),
    "policy_rules": (
        "tolerance_threshold_percent",
        "tolerance_threshold_amount",
        "routing_guidance",
        "policy_anchor_reference",
    ),
    "receiving_summary": ("receipt_status", "received_amount", "receipt_reference"),
    "contract_reference": ("contract_id", "contract_title", "contract_anchor_reference"),
    "prior_analyst_notes": ("note_summary", "note_reference"),
    "upstream_exception_flags": ("source_system", "flags"),
}

