"""PoC A acceptance-criteria reporting workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


POC_A_ACCEPTANCE_CRITERIA = (
    "A1_one_case_in_one_triage_out_flow_is_clear_and_bounded",
    "A2_output_schema_is_valid_and_stable",
    "A3_recommendation_is_understandable_to_ap_analyst",
    "A4_system_remains_within_bounded_retry_repair_envelope",
    "A5_no_unintended_downstream_automation",
    "A6_run_trace_and_audit_record_are_available",
)


@dataclass(frozen=True)
class AcceptanceCriterionAssessment:
    """One PoC A acceptance criterion assessment entry."""

    score: int | None
    passed: bool | None
    evidence: str


@dataclass(frozen=True)
class PocAAcceptanceReport:
    """Reusable PoC A acceptance report for one implementation."""

    implementation_id: str
    criteria: dict


def create_acceptance_report_template(implementation_id: str) -> dict:
    """Create an empty PoC A acceptance report template."""
    criteria = {
        criterion: {
            "score": None,
            "passed": None,
            "evidence": "",
        }
        for criterion in POC_A_ACCEPTANCE_CRITERIA
    }
    report = PocAAcceptanceReport(
        implementation_id=implementation_id,
        criteria=criteria,
    )
    return {
        "implementation_id": report.implementation_id,
        "criteria": report.criteria,
    }


def save_acceptance_report(path: Path, report: dict) -> None:
    """Persist an acceptance report artifact to JSON."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
