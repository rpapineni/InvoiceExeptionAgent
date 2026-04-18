"""Bounded PoC B end-to-end demo runner."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from invoice_exception_poc_a.audit.trace import build_poc_b_trace_sequence, build_trace_event
from invoice_exception_poc_a.config.settings import get_settings
from invoice_exception_poc_a.intake.service import (
    build_case_envelope,
    load_case_envelope,
    validate_case_payload,
)
from invoice_exception_poc_a.memory import (
    build_reviewed_case_summary,
    build_vendor_exception_profile,
    persist_reviewed_outcome_to_decision_memory,
    validate_reviewed_case_writeback,
)
from invoice_exception_poc_a.normalization.service import normalize_case
from invoice_exception_poc_a.review import validate_reviewer_feedback
from invoice_exception_poc_a.schema.output import build_placeholder_output
from invoice_exception_poc_a.telemetry import build_decision_path_telemetry, validate_decision_path_telemetry
from invoice_exception_poc_a.triage.orchestrator import run_triage


REPO_ROOT = Path(__file__).resolve().parents[2]
CURATED_POC_B_DEMO_CASES = {
    "sample_case": REPO_ROOT / "samples" / "sample_case.json",
    "mixed_signal_ambiguous": (
        REPO_ROOT
        / "invoice_exception_poc_a"
        / "evaluation"
        / "dataset_pack"
        / "cases"
        / "mixed_signal_ambiguous.json"
    ),
}


def run_poc_b_demo(
    *,
    case_input: str | Path | dict,
    reviewer_feedback: dict,
    writeback_signals: dict,
    settings=None,
    output_dir: str | Path | None = None,
) -> dict:
    """Run the bounded PoC B demo flow and return an inspectable artifact bundle."""
    settings = settings or get_settings()
    reviewer_feedback = validate_reviewer_feedback(reviewer_feedback)

    started = time.perf_counter()
    execution_trace: list[dict] = [
        build_trace_event(
            "triage_engine_selection",
            "completed",
            f"Selected triage engine '{settings.triage_engine}'.",
        )
    ]
    case_envelope, case_source = _resolve_demo_case_input(case_input, settings)
    execution_trace.append(build_trace_event("intake", "completed", "Loaded one validated demo case envelope."))
    normalized_case = normalize_case(case_envelope)
    execution_trace.append(build_trace_event("normalization", "completed", "Normalized canonical demo case facts."))

    triage_result = run_triage(normalized_case, settings, execution_trace)
    triage_output = build_placeholder_output(
        normalized_case,
        triage_result,
        settings,
        latency_ms=(time.perf_counter() - started) * 1000,
        retry_count=0,
        execution_trace=triage_result["execution_trace"],
    )
    _validate_demo_feedback_alignment(triage_output, reviewer_feedback)

    validated_writeback = validate_reviewed_case_writeback(
        triage_output={
            "exception_type": triage_output["exception_type"],
            "recommended_owner": triage_output["recommended_owner"],
            "confidence": triage_output["confidence"],
        },
        reviewer_feedback=reviewer_feedback,
        writeback_signals=writeback_signals,
    )
    decision_memory = persist_reviewed_outcome_to_decision_memory(
        triage_output={
            "case_id": triage_output["case_id"],
            "exception_type": triage_output["exception_type"],
            "recommended_owner": triage_output["recommended_owner"],
            "confidence": triage_output["confidence"],
        },
        reviewer_feedback=reviewer_feedback,
        writeback_signals=writeback_signals,
        vendor_exception_profile=_derive_vendor_profile_seed(normalized_case),
    )
    reviewed_case_summary = build_reviewed_case_summary(decision_memory=decision_memory)

    vendor_exception_profile = None
    if _vendor_profile_applicable(normalized_case):
        vendor_exception_profile = build_vendor_exception_profile(
            decision_memory=decision_memory,
            reviewed_case_summary=reviewed_case_summary,
        )

    selected_path = writeback_signals.get("decision_path") or _infer_selected_path(settings.triage_engine)
    telemetry = validate_decision_path_telemetry(
        build_decision_path_telemetry(
            selected_path=selected_path,
            path_transitions=[selected_path],
            escalation_reason=writeback_signals.get("escalation_reason"),
            retry_count=triage_output["run_metadata"]["retry_count"],
            latency_ms=triage_output["run_metadata"]["latency_ms"],
            human_review_required=True,
            usage_summary=writeback_signals["usage_summary"],
            engine_mode=settings.triage_engine,
            path_confidence_source=triage_output["confidence"],
            decision_path_version="poc_b_demo_v1",
            bounded_notes=["Demo telemetry for the PoC B reviewed-case value loop."],
        )
    )
    bounded_trace = build_poc_b_trace_sequence(
        selected_path=selected_path,
        human_review_required=True,
    )

    bundle = {
        "demo_bundle_version": "poc_b_demo_v1",
        "case_source": case_source,
        "case_id": triage_output["case_id"],
        "triage_output": triage_output,
        "reviewer_feedback": reviewer_feedback,
        "validated_writeback": validated_writeback,
        "decision_memory": decision_memory,
        "reviewed_case_summary": reviewed_case_summary,
        "vendor_exception_profile": vendor_exception_profile,
        "telemetry": telemetry,
        "bounded_trace": bounded_trace,
        "reuse_preview": {
            "decision_memory_created": True,
            "reviewed_case_summary_created": True,
            "vendor_exception_profile_created": vendor_exception_profile is not None,
        },
    }

    if output_dir is not None:
        bundle_path = write_demo_artifact_bundle(bundle, output_dir)
        bundle["artifact_bundle_path"] = str(bundle_path)

    return bundle


def write_demo_artifact_bundle(bundle: dict, output_dir: str | Path) -> Path:
    """Write the demo artifact bundle to a stable JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    bundle_path = output_path / f"{bundle['case_id']}-poc-b-demo-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return bundle_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded PoC B end-to-end demo flow.")
    parser.add_argument("--input", help="Path to a JSON case file or curated demo case name.")
    parser.add_argument("--reviewer-feedback", required=True, help="Path to structured reviewer feedback JSON.")
    parser.add_argument("--writeback-signals", required=True, help="Path to bounded writeback signals JSON.")
    parser.add_argument("--output-dir", help="Optional directory for the demo artifact bundle JSON.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        reviewer_feedback = json.loads(Path(args.reviewer_feedback).read_text(encoding="utf-8"))
        writeback_signals = json.loads(Path(args.writeback_signals).read_text(encoding="utf-8"))
        case_input = args.input or "sample_case"
        bundle = run_poc_b_demo(
            case_input=case_input,
            reviewer_feedback=reviewer_feedback,
            writeback_signals=writeback_signals,
            output_dir=args.output_dir,
        )
        print(json.dumps(bundle, indent=2))
        return 0
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1


def _resolve_demo_case_input(case_input: str | Path | dict, settings) -> tuple[dict, str]:
    if isinstance(case_input, dict):
        validated_case = validate_case_payload(case_input)
        return build_case_envelope(validated_case, settings), "inline_case_payload"

    if isinstance(case_input, Path):
        return load_case_envelope(case_input, settings), str(case_input)

    if case_input in CURATED_POC_B_DEMO_CASES:
        case_path = CURATED_POC_B_DEMO_CASES[case_input]
        return load_case_envelope(case_path, settings), case_input

    case_path = Path(case_input)
    return load_case_envelope(case_path, settings), str(case_path)


def _derive_vendor_profile_seed(normalized_case: dict) -> dict | None:
    vendor_id = normalized_case["vendor_facts"].get("vendor_id")
    vendor_name = normalized_case["vendor_facts"].get("canonical_vendor_name")
    if not vendor_id and not vendor_name:
        return None
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "profile_scope": "demo_runner_vendor_pattern",
    }


def _vendor_profile_applicable(normalized_case: dict) -> bool:
    vendor_facts = normalized_case["vendor_facts"]
    return bool(vendor_facts.get("vendor_id") or vendor_facts.get("canonical_vendor_name"))


def _infer_selected_path(triage_engine: str) -> str:
    return "full_reasoning" if triage_engine == "frontier" else "deterministic"


def _validate_demo_feedback_alignment(triage_output: dict, reviewer_feedback: dict) -> None:
    if reviewer_feedback["predicted_label"] != triage_output["exception_type"]:
        raise ValueError(
            "Reviewer feedback predicted_label must match the first-pass triage exception_type for the demo runner."
        )
    if reviewer_feedback["predicted_owner"] != triage_output["recommended_owner"]:
        raise ValueError(
            "Reviewer feedback predicted_owner must match the first-pass triage recommended_owner for the demo runner."
        )


if __name__ == "__main__":
    raise SystemExit(main())
