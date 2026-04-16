"""Internal case envelope for PoC A intake assembly."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvelopeMetadata:
    """Per-run metadata attached to one case envelope."""

    case_id: str
    run_id: str
    run_started_at: str
    workflow_version: str
    prompt_version: str
    app_env: str


@dataclass(frozen=True)
class CaseEnvelope:
    """Single internal envelope containing validated case context and metadata."""

    metadata: EnvelopeMetadata
    source_payload: dict
    invoice: dict
    po_summary: dict
    vendor_master: dict
    policy_rules: dict
    receiving_summary: dict | None
    contract_reference: dict | None
    prior_analyst_notes: dict | None
    upstream_exception_flags: dict | None
