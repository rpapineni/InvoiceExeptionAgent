"""Case intake for a single invoice exception case."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from invoice_exception_poc_a.intake.contract import REQUIRED_TOP_LEVEL_FIELDS, SECTION_FIELD_RULES
from invoice_exception_poc_a.intake.envelope import CaseEnvelope, EnvelopeMetadata


def load_case(path: Path) -> dict:
    """Load exactly one case from JSON input."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        raise ValueError("PoC A supports exactly one case per invocation; arrays are not allowed.")

    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object representing one case.")

    if "cases" in payload:
        cases = payload["cases"]
        if isinstance(cases, list):
            if len(cases) != 1:
                raise ValueError(
                    "PoC A supports exactly one case per invocation; multiple cases were provided."
                )
            return validate_case_payload(cases[0])

    if _looks_like_dataset_case_wrapper(payload):
        return validate_case_payload(payload["input_payload"])

    return validate_case_payload(payload)


def _looks_like_dataset_case_wrapper(payload: dict) -> bool:
    """Return True when the JSON object is a dataset wrapper around one input payload."""
    input_payload = payload.get("input_payload")
    return (
        isinstance(input_payload, dict)
        and "case_id" in payload
        and "expected_outcome" in payload
        and "coverage_bucket" in payload
    )


def load_case_envelope(path: Path, settings) -> dict:
    """Load one valid case and assemble a single internal case envelope."""
    validated_case = load_case(path)
    return build_case_envelope(validated_case, settings)


def build_case_envelope(validated_case: dict, settings) -> dict:
    """Attach run metadata and package validated input for downstream stages."""
    metadata = EnvelopeMetadata(
        case_id=validated_case["case_id"],
        run_id=str(uuid.uuid4()),
        run_started_at=datetime.now(UTC).isoformat(),
        workflow_version=settings.workflow_version,
        prompt_version=settings.prompt_version,
        app_env=settings.app_env,
    )
    envelope = CaseEnvelope(
        metadata=metadata,
        source_payload=validated_case,
        invoice=validated_case["invoice"],
        po_summary=validated_case["po_summary"],
        vendor_master=validated_case["vendor_master"],
        policy_rules=validated_case["policy_rules"],
        receiving_summary=validated_case.get("receiving_summary"),
        contract_reference=validated_case.get("contract_reference"),
        prior_analyst_notes=validated_case.get("prior_analyst_notes"),
        upstream_exception_flags=validated_case.get("upstream_exception_flags"),
    )
    return {
        "metadata": {
            "case_id": envelope.metadata.case_id,
            "run_id": envelope.metadata.run_id,
            "run_started_at": envelope.metadata.run_started_at,
            "workflow_version": envelope.metadata.workflow_version,
            "prompt_version": envelope.metadata.prompt_version,
            "app_env": envelope.metadata.app_env,
        },
        "source_payload": envelope.source_payload,
        "invoice": envelope.invoice,
        "po_summary": envelope.po_summary,
        "vendor_master": envelope.vendor_master,
        "policy_rules": envelope.policy_rules,
        "receiving_summary": envelope.receiving_summary,
        "contract_reference": envelope.contract_reference,
        "prior_analyst_notes": envelope.prior_analyst_notes,
        "upstream_exception_flags": envelope.upstream_exception_flags,
    }


def validate_case_payload(payload: dict) -> dict:
    """Validate the formal one-case PoC A input contract."""
    missing_top_level = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in payload]
    if missing_top_level:
        missing = ", ".join(missing_top_level)
        raise ValueError(f"Missing required top-level field(s): {missing}.")

    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Field 'case_id' must be a non-empty string.")

    for section_name in REQUIRED_TOP_LEVEL_FIELDS[1:] + tuple(
        name for name in SECTION_FIELD_RULES if name not in REQUIRED_TOP_LEVEL_FIELDS
    ):
        if section_name not in payload:
            continue
        _validate_section(section_name, payload[section_name])

    return payload


def _validate_section(section_name: str, section_value: object) -> None:
    """Validate a top-level section against the formal contract."""
    if not isinstance(section_value, dict):
        raise ValueError(f"Field '{section_name}' must be a JSON object.")

    required_fields = SECTION_FIELD_RULES[section_name]
    missing_fields = [field for field in required_fields if field not in section_value]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Field '{section_name}' is missing required field(s): {missing}.")

    for field_name in required_fields:
        field_value = section_value[field_name]
        if isinstance(field_value, str) and not field_value.strip():
            raise ValueError(f"Field '{section_name}.{field_name}' must be a non-empty string.")
        if field_name == "flags":
            if not isinstance(field_value, list) or any(
                not isinstance(item, str) or not item.strip() for item in field_value
            ):
                raise ValueError("Field 'upstream_exception_flags.flags' must be a list of strings.")
