"""Dual-run comparison helpers for deterministic and frontier PoC A execution."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from invoice_exception_poc_a.audit.trace import build_trace_event
from invoice_exception_poc_a.config.settings import FrontierSettings, Settings
from invoice_exception_poc_a.evaluation.dataset import load_dataset_case, load_dataset_manifest
from invoice_exception_poc_a.intake.service import build_case_envelope, validate_case_payload
from invoice_exception_poc_a.normalization.service import normalize_case
from invoice_exception_poc_a.schema.output import build_placeholder_output
from invoice_exception_poc_a.triage.orchestrator import run_triage


def run_case_for_engine(
    case_payload: dict,
    *,
    engine_mode: str,
    frontier_provider: str = "stub",
    frontier_model: str = "stub-placeholder-v1",
    frontier_adapter_override=None,
) -> dict:
    """Run one validated case through one configured engine mode."""
    settings = _build_settings_for_engine(
        engine_mode=engine_mode,
        frontier_provider=frontier_provider,
        frontier_model=frontier_model,
    )
    execution_trace = [
        build_trace_event(
            "triage_engine_selection",
            "completed",
            f"Selected triage engine '{settings.triage_engine}'.",
        )
    ]
    validated_case = validate_case_payload(case_payload)
    case_envelope = build_case_envelope(validated_case, settings)
    execution_trace.append(build_trace_event("intake", "completed", "Loaded one validated case envelope."))
    normalized_case = normalize_case(case_envelope)
    execution_trace.append(build_trace_event("normalization", "completed", "Normalized canonical case facts."))
    triage_result = run_triage(
        normalized_case,
        settings,
        execution_trace,
        frontier_adapter_override=frontier_adapter_override,
    )
    output = build_placeholder_output(
        normalized_case,
        triage_result,
        settings,
        latency_ms=5.0,
        retry_count=0,
        execution_trace=triage_result["execution_trace"],
    )
    return {
        "engine_mode": engine_mode,
        "output_payload": output,
    }


def build_comparison_record(
    dataset_case: dict,
    *,
    frontier_provider: str = "stub",
    frontier_model: str = "stub-placeholder-v1",
    frontier_adapter_override=None,
) -> dict:
    """Build one side-by-side deterministic/frontier comparison record."""
    case_payload = dataset_case["input_payload"]
    deterministic_result = run_case_for_engine(case_payload, engine_mode="deterministic")
    frontier_result = run_case_for_engine(
        case_payload,
        engine_mode="frontier",
        frontier_provider=frontier_provider,
        frontier_model=frontier_model,
        frontier_adapter_override=frontier_adapter_override,
    )
    return {
        "case_id": dataset_case["case_id"],
        "coverage_bucket": dataset_case["coverage_bucket"],
        "case_description": dataset_case["case_description"],
        "deterministic_output": deterministic_result["output_payload"],
        "frontier_output": frontier_result["output_payload"],
        "reviewer_notes": "",
    }


def build_dual_run_comparison_report(
    *,
    case_filenames: list[str] | None = None,
    frontier_provider: str = "stub",
    frontier_model: str = "stub-placeholder-v1",
    frontier_adapter_override=None,
) -> dict:
    """Run a dataset subset through both engines and return a comparison-ready report."""
    manifest = load_dataset_manifest()
    entries = manifest["cases"]
    if case_filenames is not None:
        requested = set(case_filenames)
        entries = [entry for entry in entries if entry["case_file"] in requested]
    records = []
    for entry in entries:
        dataset_case = load_dataset_case(entry["case_file"])
        records.append(
            build_comparison_record(
                dataset_case,
                frontier_provider=frontier_provider,
                frontier_model=frontier_model,
                frontier_adapter_override=frontier_adapter_override,
            )
        )
    return {
        "comparison_run_id": f"comparison-{uuid4()}",
        "frontier_provider": frontier_provider,
        "frontier_model": frontier_model,
        "records": records,
    }


def save_dual_run_comparison_report(report: dict, destination: Path) -> None:
    """Persist a comparison report for later review."""
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _build_settings_for_engine(
    *,
    engine_mode: str,
    frontier_provider: str,
    frontier_model: str,
) -> Settings:
    return Settings(
        workflow_version="0.1.0",
        prompt_version="placeholder-prompt-v1",
        app_env="local",
        triage_engine=engine_mode,
        frontier=FrontierSettings(
            provider=frontier_provider if engine_mode == "frontier" else None,
            model=frontier_model if engine_mode == "frontier" else None,
        ),
    )
