"""Formal PoC A output contract."""

from __future__ import annotations

from dataclasses import dataclass


OUTPUT_REQUIRED_FIELDS = (
    "case_id",
    "exception_type",
    "reason_summary",
    "recommended_owner",
    "priority",
    "next_actions",
    "questions_for_reviewer",
    "confidence",
)

OUTPUT_OPTIONAL_FIELDS = (
    "run_id",
    "workflow_version",
    "prompt_version",
    "app_env",
    "schema_version",
)

ALLOWED_CONFIDENCE_VALUES = ("high", "medium", "low")
ALLOWED_PRIORITY_VALUES = ("low", "medium", "high")
ALLOWED_VALIDATION_STATUSES = ("valid", "repaired_valid", "failed")


@dataclass(frozen=True)
class PocAOutput:
    """Formal comparable PoC A output payload."""

    case_id: str
    exception_type: str
    reason_summary: str
    recommended_owner: str
    priority: str
    next_actions: list[str]
    questions_for_reviewer: list[str]
    confidence: str
    run_id: str
    workflow_version: str
    prompt_version: str
    app_env: str
    schema_version: str


@dataclass(frozen=True)
class OutputValidationResult:
    """Bounded validation result for the formal PoC A output payload."""

    output: dict
    validation_status: str
    validation_errors: list[str]
    repair_attempted: bool
    repair_count: int
