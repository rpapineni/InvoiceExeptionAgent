"""Dedicated parsing and normalization for bounded frontier judgment output."""

from __future__ import annotations

from invoice_exception_poc_a.frontier_prompt import REQUIRED_FRONTIER_OUTPUT_FIELDS


SCALAR_FIELDS = (
    "exception_type",
    "reason_summary",
    "recommended_owner",
    "priority",
    "confidence",
)
LIST_FIELDS = ("next_actions", "questions_for_reviewer")


def parse_frontier_judgment_to_poc_a_output(parsed_output: dict, *, case_id: str) -> dict:
    """Normalize bounded frontier judgment content into the PoC A output field shape."""
    if not isinstance(parsed_output, dict):
        raise ValueError("Frontier adapter response payload must be a dictionary.")

    missing_fields = [field for field in REQUIRED_FRONTIER_OUTPUT_FIELDS if field not in parsed_output]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Frontier adapter response is missing required field(s): {missing}.")

    normalized = {"case_id": case_id}

    for field in SCALAR_FIELDS:
        value = parsed_output[field]
        if not isinstance(value, str):
            raise ValueError(f"Frontier adapter response field '{field}' must be a non-empty string.")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"Frontier adapter response field '{field}' must be a non-empty string.")
        normalized[field] = normalized_value

    for field in LIST_FIELDS:
        value = parsed_output[field]
        normalized[field] = _normalize_string_list_field(field, value)

    return normalized


def normalize_frontier_judgment_for_validation(parsed_output: dict, *, case_id: str) -> dict:
    """Build a PoC A schema-shaped frontier output candidate for shared validation reuse."""
    if not isinstance(parsed_output, dict):
        raise ValueError("Frontier adapter response payload must be a dictionary.")

    normalized = {"case_id": case_id}
    for field in SCALAR_FIELDS:
        normalized[field] = _normalize_optional_scalar(parsed_output.get(field))
    for field in LIST_FIELDS:
        normalized[field] = _normalize_optional_list_field(parsed_output.get(field))
    return normalized


def _normalize_string_list_field(field: str, value: object) -> list[str]:
    if isinstance(value, str):
        normalized_scalar = value.strip()
        if not normalized_scalar:
            raise ValueError(f"Frontier adapter response field '{field}' must not be empty.")
        return [normalized_scalar]
    if not isinstance(value, list):
        raise ValueError(f"Frontier adapter response field '{field}' must be a list of non-empty strings.")

    normalized_items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"Frontier adapter response field '{field}' must be a list of non-empty strings.")
        normalized_item = item.strip()
        if not normalized_item:
            raise ValueError(f"Frontier adapter response field '{field}' must contain only non-empty strings.")
        normalized_items.append(normalized_item)
    return normalized_items


def _normalize_optional_scalar(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_optional_list_field(value: object) -> object:
    if isinstance(value, str):
        return [value.strip()]
    if isinstance(value, list):
        normalized_items: list[object] = []
        for item in value:
            if isinstance(item, str):
                normalized_items.append(item.strip())
            else:
                normalized_items.append(item)
        return normalized_items
    return value
