"""Bounded validation and repair for the formal PoC A output schema."""

from __future__ import annotations

from copy import deepcopy

from invoice_exception_poc_a.schema.model import (
    ALLOWED_CONFIDENCE_VALUES,
    ALLOWED_PRIORITY_VALUES,
    ALLOWED_VALIDATION_STATUSES,
    OUTPUT_REQUIRED_FIELDS,
    OutputValidationResult,
)


LIST_FIELDS = ("next_actions", "questions_for_reviewer")
STRING_FIELDS = (
    "case_id",
    "exception_type",
    "reason_summary",
    "recommended_owner",
    "priority",
    "confidence",
)
OPTIONAL_METADATA_FIELDS = ("run_id", "workflow_version", "prompt_version", "app_env", "schema_version")
MAX_REPAIR_COUNT = 1
DEFAULT_SCHEMA_VERSION = "1.0.0"


def validate_output_payload(payload: dict, runtime_context: dict | None = None) -> OutputValidationResult:
    """Validate the PoC A output payload and attempt one bounded repair pass."""
    errors = _collect_validation_errors(payload)
    if not errors:
        return _result(payload, "valid", [], False, 0)

    repaired_payload = _attempt_repair(payload, runtime_context or {})
    repaired_errors = _collect_validation_errors(repaired_payload)
    repaired = repaired_payload != payload
    if repaired and not repaired_errors:
        return _result(repaired_payload, "repaired_valid", [], True, 1)

    final_errors = repaired_errors if repaired else errors
    return _result(repaired_payload, "failed", final_errors, repaired, 1 if repaired else 0)


def _result(
    payload: dict,
    status: str,
    errors: list[str],
    repair_attempted: bool,
    repair_count: int,
) -> OutputValidationResult:
    if status not in ALLOWED_VALIDATION_STATUSES:
        raise ValueError(f"Unsupported validation status: {status}")
    return OutputValidationResult(
        output=payload,
        validation_status=status,
        validation_errors=errors,
        repair_attempted=repair_attempted,
        repair_count=min(repair_count, MAX_REPAIR_COUNT),
    )


def _collect_validation_errors(payload: dict) -> list[str]:
    errors: list[str] = []

    for field in OUTPUT_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}.")

    for field in STRING_FIELDS:
        if field in payload and (not isinstance(payload[field], str) or not payload[field].strip()):
            errors.append(f"Field '{field}' must be a non-empty string.")

    for field in LIST_FIELDS:
        if field in payload:
            if not isinstance(payload[field], list):
                errors.append(f"Field '{field}' must be a list of strings.")
            elif any(not isinstance(item, str) or not item.strip() for item in payload[field]):
                errors.append(f"Field '{field}' must contain only non-empty strings.")

    if "priority" in payload and payload.get("priority") not in ALLOWED_PRIORITY_VALUES:
        errors.append("Field 'priority' must be one of: " + ", ".join(ALLOWED_PRIORITY_VALUES) + ".")

    if "confidence" in payload and payload.get("confidence") not in ALLOWED_CONFIDENCE_VALUES:
        errors.append("Field 'confidence' must be one of: " + ", ".join(ALLOWED_CONFIDENCE_VALUES) + ".")

    for field in OPTIONAL_METADATA_FIELDS:
        if field in payload and payload[field] is not None and not isinstance(payload[field], str):
            errors.append(f"Optional field '{field}' must be a string when present.")

    return errors


def _attempt_repair(payload: dict, runtime_context: dict) -> dict:
    repaired = deepcopy(payload)

    for field in LIST_FIELDS:
        value = repaired.get(field)
        if isinstance(value, str) and value.strip():
            repaired[field] = [value]

    for field in ("priority", "confidence"):
        value = repaired.get(field)
        if isinstance(value, str):
            repaired[field] = value.lower()

    optional_defaults = {
        "run_id": runtime_context.get("run_id"),
        "workflow_version": runtime_context.get("workflow_version"),
        "prompt_version": runtime_context.get("prompt_version"),
        "app_env": runtime_context.get("app_env"),
        "schema_version": runtime_context.get("schema_version", DEFAULT_SCHEMA_VERSION),
    }
    for field, default_value in optional_defaults.items():
        if field not in repaired and default_value is not None:
            repaired[field] = default_value

    return repaired
