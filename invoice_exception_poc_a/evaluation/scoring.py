"""Lightweight business-quality scoring workflow for PoC A evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from invoice_exception_poc_a.evaluation.dataset import load_dataset_case, load_dataset_manifest


BUSINESS_QUALITY_METRICS = (
    "primary_exception_classification_quality",
    "recommended_owner_quality",
    "reason_summary_clarity",
    "next_action_usefulness",
    "question_surfacing_uncertainty_handling",
    "analyst_trust_acceptability",
)


@dataclass(frozen=True)
class MetricScore:
    """One 1-5 business-quality score plus supporting evidence."""

    score: int | None
    evidence: str


@dataclass(frozen=True)
class BusinessQualityScoreRecord:
    """Reviewer-oriented business-quality scoring record for one dataset case."""

    case_id: str
    coverage_bucket: str
    expected_primary_exception_type: str
    expected_likely_owner: str
    metric_scores: dict


def create_score_record(case_id: str) -> dict:
    """Create an empty score record for one dataset case."""
    manifest = load_dataset_manifest()
    manifest_entry = next(entry for entry in manifest["cases"] if entry["case_id"] == case_id)
    case_data = load_dataset_case(manifest_entry["case_file"])
    metric_scores = {
        metric: {"score": None, "evidence": ""}
        for metric in BUSINESS_QUALITY_METRICS
    }
    record = BusinessQualityScoreRecord(
        case_id=case_data["case_id"],
        coverage_bucket=case_data["coverage_bucket"],
        expected_primary_exception_type=case_data["expected_outcome"]["primary_exception_type"],
        expected_likely_owner=case_data["expected_outcome"]["likely_owner"],
        metric_scores=metric_scores,
    )
    return {
        "case_id": record.case_id,
        "coverage_bucket": record.coverage_bucket,
        "expected_primary_exception_type": record.expected_primary_exception_type,
        "expected_likely_owner": record.expected_likely_owner,
        "metric_scores": record.metric_scores,
    }


def create_all_score_records() -> list[dict]:
    """Create empty score records for the full dataset pack."""
    manifest = load_dataset_manifest()
    return [create_score_record(entry["case_id"]) for entry in manifest["cases"]]


def save_score_records(path: Path, records: list[dict]) -> None:
    """Persist score records to a simple JSON artifact."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)
