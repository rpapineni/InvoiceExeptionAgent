"""Lightweight operational metrics reporting for PoC A evaluation runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricValueWithNote:
    """Metric value plus an explicit note about assumptions or availability."""

    value: float | int | None
    note: str


@dataclass(frozen=True)
class OperationalMetricsReport:
    """Aggregate operational metrics for a set of PoC A outputs."""

    total_cases: int
    average_latency_per_case: MetricValueWithNote
    average_retries_per_case: MetricValueWithNote
    average_token_or_compute_usage_per_case: MetricValueWithNote
    valid_structured_output_rate: MetricValueWithNote
    estimated_analyst_time_saved: MetricValueWithNote


def create_operational_metrics_report(outputs: list[dict]) -> dict:
    """Create an aggregate operational metrics report from PoC A outputs."""
    total_cases = len(outputs)
    latencies = [output["run_metadata"]["latency_ms"] for output in outputs]
    retries = [output["run_metadata"]["retry_count"] for output in outputs]
    valid_count = sum(1 for output in outputs if output.get("validation_status") in ("valid", "repaired_valid"))

    token_values = [output["run_metadata"].get("token_usage") for output in outputs]
    compute_values = [output["run_metadata"].get("compute_usage") for output in outputs]
    measurable_usage = [value for value in token_values if value is not None]

    token_usage_note = (
        "Token usage is unavailable in the current local stack; compute usage placeholders were present but non-numeric."
        if not measurable_usage
        else "Average token usage was computed from available run metadata."
    )

    report = OperationalMetricsReport(
        total_cases=total_cases,
        average_latency_per_case=MetricValueWithNote(
            value=_safe_average(latencies),
            note="Average latency was computed from run_metadata.latency_ms.",
        ),
        average_retries_per_case=MetricValueWithNote(
            value=_safe_average(retries),
            note="Average retries were computed from run_metadata.retry_count.",
        ),
        average_token_or_compute_usage_per_case=MetricValueWithNote(
            value=_safe_average(measurable_usage),
            note=token_usage_note,
        ),
        valid_structured_output_rate=MetricValueWithNote(
            value=round(valid_count / total_cases, 3) if total_cases else None,
            note="Rate is based on validation_status values of valid or repaired_valid.",
        ),
        estimated_analyst_time_saved=MetricValueWithNote(
            value=None,
            note="Estimated analyst time saved is a manual or external estimate at this stage and is not automatically computed.",
        ),
    )
    return {
        "total_cases": report.total_cases,
        "average_latency_per_case": {
            "value": report.average_latency_per_case.value,
            "note": report.average_latency_per_case.note,
        },
        "average_retries_per_case": {
            "value": report.average_retries_per_case.value,
            "note": report.average_retries_per_case.note,
        },
        "average_token_or_compute_usage_per_case": {
            "value": report.average_token_or_compute_usage_per_case.value,
            "note": report.average_token_or_compute_usage_per_case.note,
        },
        "valid_structured_output_rate": {
            "value": report.valid_structured_output_rate.value,
            "note": report.valid_structured_output_rate.note,
        },
        "estimated_analyst_time_saved": {
            "value": report.estimated_analyst_time_saved.value,
            "note": report.estimated_analyst_time_saved.note,
        },
    }


def save_operational_metrics_report(path: Path, report: dict) -> None:
    """Persist an operational metrics report to JSON."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


def _safe_average(values: list[float | int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)
