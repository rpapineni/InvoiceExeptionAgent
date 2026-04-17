"""Versioned structured prompt contract for frontier triage."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from invoice_exception_poc_a.triage.model import (
    CONFIDENCE_SCALE,
    EXCEPTION_TAXONOMY,
    OWNER_CATEGORIES,
    PRIORITY_SCALE,
)


FRONTIER_TRIAGE_PROMPT_VERSION = "frontier-triage-v1"
REQUIRED_FRONTIER_OUTPUT_FIELDS = (
    "exception_type",
    "reason_summary",
    "recommended_owner",
    "priority",
    "next_actions",
    "questions_for_reviewer",
    "confidence",
)


@dataclass(frozen=True)
class FrontierPromptContract:
    """Provider-agnostic structured prompt package for bounded frontier triage."""

    contract_version: str
    prompt_version: str
    system_instructions: str
    user_payload: dict


def build_frontier_triage_prompt(
    normalized_case: dict,
    *,
    uncertainty_section: dict | None = None,
    prompt_version: str | None = None,
) -> dict:
    """Build a strict prompt contract from normalized facts and structured uncertainty."""
    prompt_contract = FrontierPromptContract(
        contract_version=FRONTIER_TRIAGE_PROMPT_VERSION,
        prompt_version=prompt_version or normalized_case.get("prompt_version") or "frontier-prompt-v1",
        system_instructions=_build_system_instructions(),
        user_payload={
            "case_id": normalized_case["case_id"],
            "normalized_case": _build_prompt_case_payload(normalized_case),
            "uncertainty": uncertainty_section or normalized_case["uncertainty"],
            "response_schema_guidance": {
                "required_fields": list(REQUIRED_FRONTIER_OUTPUT_FIELDS),
                "allowed_exception_types": list(EXCEPTION_TAXONOMY),
                "allowed_recommended_owners": list(OWNER_CATEGORIES),
                "allowed_priority_values": list(PRIORITY_SCALE),
                "allowed_confidence_values": list(CONFIDENCE_SCALE),
            },
        },
    )
    return asdict(prompt_contract)


def _build_system_instructions() -> str:
    output_fields = ", ".join(REQUIRED_FRONTIER_OUTPUT_FIELDS)
    exception_values = ", ".join(EXCEPTION_TAXONOMY)
    owner_values = ", ".join(OWNER_CATEGORIES)
    priority_values = ", ".join(PRIORITY_SCALE)
    confidence_values = ", ".join(CONFIDENCE_SCALE)
    return (
        f"You are the bounded frontier triage judgment layer for PoC A-F. "
        f"Return valid JSON only with no surrounding prose, markdown, or commentary. "
        f"Return exactly these top-level fields: {output_fields}. "
        f"Use normalized facts only. Use uncertainty signals when relevant. "
        f"Return exactly one primary exception_type. "
        f"Allowed exception_type values: {exception_values}. "
        f"Allowed recommended_owner values: {owner_values}. "
        f"Allowed priority values: {priority_values}. "
        f"Allowed confidence values: {confidence_values}. "
        f"Keep reason_summary grounded in case facts and avoid unsupported claims. "
        f"Keep next_actions reviewer-oriented and do not imply autonomous execution. "
        f"Keep questions_for_reviewer tied to missing or conflicting facts. "
        f"Do not use downstream action language. "
        f"Do not reference memory, prior cases, prior corrections, or cross-case patterns. "
        f"Do not route, approve, reject, pay, notify, post to ERP, or use uncontrolled tools. "
        f"Stay inside PoC A boundaries only."
    )


def _build_prompt_case_payload(normalized_case: dict) -> dict:
    return {
        "case_metadata": {
            "case_id": normalized_case["case_id"],
            "workflow_version": normalized_case["workflow_version"],
            "app_env": normalized_case["app_env"],
        },
        "invoice_facts": normalized_case["invoice_facts"],
        "po_facts": normalized_case["po_facts"],
        "vendor_facts": normalized_case["vendor_facts"],
        "policy_facts": normalized_case["policy_facts"],
        "receiving_summary": normalized_case["receiving_summary"],
        "contract_reference": normalized_case["contract_reference"],
        "prior_analyst_notes": normalized_case["prior_analyst_notes"],
        "upstream_exception_flags": normalized_case["upstream_exception_flags"],
    }
