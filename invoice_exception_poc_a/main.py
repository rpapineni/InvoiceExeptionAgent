"""Single-case entry point for PoC A."""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path

from invoice_exception_poc_a.audit.trace import build_trace_event
from invoice_exception_poc_a.config.settings import get_settings
from invoice_exception_poc_a.intake.service import load_case_envelope
from invoice_exception_poc_a.normalization.service import normalize_case
from invoice_exception_poc_a.schema.output import build_placeholder_output
from invoice_exception_poc_a.triage.orchestrator import run_triage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PoC A bounded first-pass triage scaffold for one case."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file containing exactly one invoice exception case.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        started = time.perf_counter()
        execution_trace: list[dict] = []
        args = parse_args()
        settings = get_settings()
        case_envelope = load_case_envelope(Path(args.input), settings)
        execution_trace.append(build_trace_event("intake", "completed", "Loaded one validated case envelope."))
        normalized_case = normalize_case(case_envelope)
        execution_trace.append(build_trace_event("normalization", "completed", "Normalized canonical case facts."))
        triage_result = run_triage(normalized_case, settings, execution_trace)
        latency_ms = (time.perf_counter() - started) * 1000
        output = build_placeholder_output(
            normalized_case,
            triage_result,
            settings,
            latency_ms=latency_ms,
            retry_count=0,
            execution_trace=triage_result["execution_trace"],
        )
        print(json.dumps(output, indent=2))
        return 0
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
