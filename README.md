# PoC A: Invoice Exception Handling - Bounded First-Pass Triage Assistant

This repository contains the implementation skeleton for PoC A of the invoice exception pilot.

## Purpose

PoC A is the control version of the pilot. It is intended to demonstrate bounded first-pass triage usefulness for a single invoice exception case. The system accepts one case, normalizes the provided context, runs a placeholder triage flow, and returns one structured recommendation object for analyst review.

## Bounded workflow

- One-case-in / one-triage-out
- Platform-neutral project shape
- Stateless across cases
- First-pass triage only
- No downstream business action is performed

## In scope for this scaffold

- Project skeleton with separated modules for intake, normalization, triage, schema, audit, evaluation, and config
- Minimal runnable entry point for one-case invocation
- Externally configurable version identifiers
- Placeholder sample input and output artifacts
- Basic tests and test stubs for startup and bounded behavior

## Out of scope

This scaffold does not implement:

- Exception reasoning
- Owner recommendation logic
- Policy interpretation
- Schema validation behavior
- Retry logic
- Persistence for cross-case memory
- Reviewer feedback capture
- Downstream routing, approval, rejection, payment, or communication
- Any PoC B functionality

## PoC A Guardrails

PoC A guardrails are defined explicitly in code so later work cannot quietly expand the system into PoC B or workflow automation behavior.

- Prior-case retrieval is unsupported
- Feedback reuse is unsupported
- Autonomous routing is unsupported
- Approve, reject, and pay actions are unsupported
- Outbound communication is unsupported
- Cross-case memory is unsupported

The runtime boundary is intentionally narrow:

- The orchestration path only produces a structured recommendation payload for analyst review
- Guardrails are exposed from a dedicated policy module and surfaced in the placeholder output
- Unsupported actions can be rejected explicitly through the guardrails module instead of being implemented accidentally
- No retrieval, persistence, or downstream execution component is initialized

## Input Contract

PoC A accepts exactly one invoice exception case as a single JSON object. The formal contract is defined in [contract.py](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/intake/contract.py).

Required top-level fields:

- `case_id`: non-empty string identifier for the case
- `invoice`: invoice details with `invoice_number`, `vendor_name`, `invoice_amount`, `currency`, and `payment_terms`
- `po_summary`: PO context with `po_number`, `buyer_name`, `po_amount`, `currency`, and `line_summary`
- `vendor_master`: vendor reference data with `vendor_id`, `vendor_name`, `payment_terms`, `payment_method`, and `vendor_status`
- `policy_rules`: policy anchor data with `tolerance_threshold_percent`, `tolerance_threshold_amount`, `routing_guidance`, and `policy_anchor_reference`

Optional top-level fields:

- `receiving_summary`: receiving context with `receipt_status`, `received_amount`, and `receipt_reference`
- `contract_reference`: contract context with `contract_id`, `contract_title`, and `contract_anchor_reference`
- `prior_analyst_notes`: prior analyst context with `note_summary` and `note_reference`
- `upstream_exception_flags`: upstream markers with `source_system` and `flags`

Validation rules:

- Arrays of cases are rejected because PoC A is one-case-in / one-triage-out
- A wrapper object containing multiple cases is rejected
- Required top-level fields must be present
- Required subfields within each provided section must be present
- Optional sections may be omitted entirely without validation failure
- `case_id` and required string fields must be non-empty

## Output Contract

PoC A returns one formal structured payload for each case. The output contract is defined in [model.py](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/schema/model.py).

Required output fields:

- `case_id`
- `exception_type`
- `reason_summary`
- `recommended_owner`
- `priority`
- `next_actions`
- `questions_for_reviewer`
- `confidence`

Optional metadata fields included in this scaffold:

- `run_id`
- `workflow_version`
- `prompt_version`
- `app_env`
- `schema_version`

Shape expectations:

- `next_actions` is always a list of reviewer-oriented action strings
- `questions_for_reviewer` is always a list of reviewer questions
- `confidence` is always one of `high`, `medium`, or `low`
- `priority` is always one of `low`, `medium`, or `high`
- Optional metadata does not replace the required baseline fields

## Output Validation

PoC A validates the live output payload against the formal contract before returning it.

- Validation distinguishes `valid`, `repaired_valid`, and `failed`
- Repair is limited to a single deterministic pass
- Repair only handles small structural issues such as string-to-list normalization for list fields, enum casing normalization, and filling optional metadata already available at runtime
- Repair does not invent missing required business content such as `exception_type`, `reason_summary`, `recommended_owner`, `priority`, `next_actions`, `questions_for_reviewer`, or `confidence`
- Validation state is surfaced as `validation_status`, `validation_errors`, `repair_attempted`, and `repair_count`

## Run Metadata

Each run now emits a hardened `run_metadata` object alongside the output payload for later audit and evaluation use.

- Required run metadata fields: `case_id`, `run_id`, `run_started_at`, `workflow_version`, `prompt_version`, `app_env`
- Runtime metrics: `retry_count` and `latency_ms`
- Usage placeholders: `token_usage` and `compute_usage` are present even when unavailable and remain `null` in the current local stack
- Validation linkage: `validation_status` and `repair_count` are also captured in `run_metadata` so later review can compare output validity and repair behavior per run
- `retry_count` is always present and currently defaults to `0` because PoC A does not implement retries

## Execution Trace

Each run also emits a bounded `execution_trace` section for concise stage-level review and debugging.

- Each trace entry contains `stage`, `status`, and an optional short `note`
- The default stage coverage is: `intake`, `normalization`, `classification`, `reason_summary`, `recommendation`, `guidance`, `schema_validation`, and `output_assembly`
- Trace notes are intentionally short and operational; they do not include verbose internal reasoning
- Successful runs include completed stage entries, and validation failures still surface a useful `schema_validation` stage status where applicable

## Evaluation Dataset Pack

PoC A includes a reusable evaluation dataset pack under [dataset_pack](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/evaluation/dataset_pack) so implementations can be compared on a shared case set.

- The manifest is [manifest.json](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/evaluation/dataset_pack/manifest.json)
- Case files live in the `cases/` subfolder and each include a case description, coverage bucket, reviewer-reference expected outcome, and an `input_payload` aligned to the PoC A input contract
- Coverage buckets are `simple_obvious`, `moderately_ambiguous`, and `edge_low_data`
- Included reviewer-reference case themes are: amount mismatch, missing PO, vendor mismatch, terms mismatch, receiving mismatch, policy tolerance breach, insufficient information, and one mixed-signal ambiguous case
- The pack is intentionally implementation-neutral and does not include score aggregation, dashboards, or PoC B repeated-pattern/learning-loop evaluation logic

## Business Quality Scoring Workflow

PoC A also includes a lightweight business-quality scoring workflow for recording reviewer assessments against the evaluation dataset.

- The scoring helper is [scoring.py](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/evaluation/scoring.py)
- Score records are keyed by dataset `case_id` and carry the expected primary exception type and likely owner from the dataset pack
- Supported metrics are:
  - `primary_exception_classification_quality`
  - `recommended_owner_quality`
  - `reason_summary_clarity`
  - `next_action_usefulness`
  - `question_surfacing_uncertainty_handling`
  - `analyst_trust_acceptability`
- Each metric supports a 1-5 `score` plus freeform `evidence`
- The workflow is intentionally lightweight and does not add efficiency aggregation, dashboards, or executive comparison tables

## Operational Metrics Workflow

PoC A also includes a lightweight operational metrics reporting workflow for summarizing efficiency-oriented measures across a set of run outputs.

- The reporting helper is [operational_metrics.py](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/evaluation/operational_metrics.py)
- Supported aggregate metrics are:
  - `average_latency_per_case`
  - `average_retries_per_case`
  - `average_token_or_compute_usage_per_case`
  - `valid_structured_output_rate`
  - `estimated_analyst_time_saved`
- Each metric is reported with a `value` plus a `note` so unavailable or assumption-based measures remain explicit
- `valid_structured_output_rate` is computed from actual `validation_status` values in PoC A outputs
- The workflow remains separate from business-quality scoring and does not add executive comparison tables or dashboards

## PoC A Acceptance Reporting Workflow

PoC A also includes a lightweight acceptance-reporting workflow aligned to the shared scorecard's PoC A criteria section.

- The acceptance helper is [acceptance_report.py](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/evaluation/acceptance_report.py)
- Reports are keyed by `implementation_id`
- Supported criteria are:
  - `A1_one_case_in_one_triage_out_flow_is_clear_and_bounded`
  - `A2_output_schema_is_valid_and_stable`
  - `A3_recommendation_is_understandable_to_ap_analyst`
  - `A4_system_remains_within_bounded_retry_repair_envelope`
  - `A5_no_unintended_downstream_automation`
  - `A6_run_trace_and_audit_record_are_available`
- Each criterion supports a 1-5 `score`, `passed`, and `evidence`
- The workflow is reusable per implementation and remains separate from business-quality scoring, operational metrics reporting, and any cross-team comparison logic

## Submission Package Skeleton

PoC A also includes a reusable submission-package skeleton for implementation handoff and packaging.

- The package folder is [submission_package](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/submission_package)
- The package index is [manifest.json](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/invoice_exception_poc_a/submission_package/manifest.json)
- Required handoff sections are represented as markdown templates for architecture, workflow, contracts, validation/trace, evaluation, scoring, metrics, acceptance reporting, test results, and business limitations
- Existing artifacts are referenced in the package where appropriate instead of duplicating implementation logic
- The package remains implementation-neutral, template-driven, and does not invent final findings or cross-team comparison content

## Current status

This implementation is a scaffold only. It provides structure, placeholders, and a minimal single-case execution path so later stories can be added without changing the bounded project shape.

## Project structure

```text
invoice_exception_poc_a/
  audit/
  config/
  evaluation/
  intake/
  normalization/
  schema/
  triage/
samples/
tests/
```

## How to run

1. From the repository root, run:

```bash
python3 -m invoice_exception_poc_a.main --input samples/sample_case.json
```

2. Optional environment overrides:

```bash
WORKFLOW_VERSION=1.1.0 python3 -m invoice_exception_poc_a.main --input samples/sample_case.json
PROMPT_VERSION=prompt-v2 python3 -m invoice_exception_poc_a.main --input samples/sample_case.json
APP_ENV=dev python3 -m invoice_exception_poc_a.main --input samples/sample_case.json
```

## Running tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Notes on statelessness

No database, vector store, memory store, replay store, or feedback store is initialized anywhere in this scaffold. Each invocation handles one case independently and exits after emitting a placeholder output object.
