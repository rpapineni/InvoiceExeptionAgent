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

## PoC B Structured Output Extension

PoC B preserves the existing PoC A-F structured triage contract and extends it rather than replacing it.

- The inherited PoC A-F business fields remain the bounded baseline output
- PoC B adds bounded extension fields for later learning-oriented traceability, including `decision_path`, `evidence_sources`, `confidence`, `rule_hits`, and `similar_case_refs`
- These extension fields support traceability and future learning support, but they do not imply that reviewer writeback, memory, retrieval, replay, or autonomous behavior is already implemented

Reference ADR:

- [ADR-0006-poc-b-structured-output-extension.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0006-poc-b-structured-output-extension.md)

## PoC B Reviewer Outcome Contract

PoC B also defines a bounded reviewer outcome contract for recording structured reviewed truth after first-pass triage.

- It distinguishes system prediction from reviewer-finalized outcome with `predicted_label`, `final_label`, `predicted_owner`, and `final_owner`
- It captures override semantics with `override_flag` and `override_notes`
- It includes `reviewer_notes` and `final_disposition` for bounded reviewed truth
- It does not imply that persistence, memory, retrieval, replay, or autonomous workflow behavior is already implemented

Reference ADR:

- [ADR-0007-poc-b-reviewer-outcome-contract.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0007-poc-b-reviewer-outcome-contract.md)

## PoC B Minimum Writeback Contract

PoC B also defines the minimum structured writeback each reviewed case must contribute for later reusable workflow intelligence.

- It includes reviewed-truth fields, routing-improvement fields, override rationale, decision traceability, reusable handling signals, and bounded usage support
- It explicitly distinguishes field provenance across system prediction, reviewer-finalized outcome, and run/usage context
- It is intended for structured and queryable reusable workflow intelligence, not generic chat-history capture
- It does not imply that persistence, decision memory, retrieval, replay, learning metrics, or autonomous workflow behavior is already implemented

Reference ADR:

- [ADR-0008-poc-b-minimum-writeback-contract.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0008-poc-b-minimum-writeback-contract.md)

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

## Frontier Branching Strategy

PoC A deterministic baseline work and PoC A-F frontier-assisted work must coexist as separate tracks so the bounded control implementation remains comparable.

Recommended branch roles:

- `release/poc-a-deterministic-baseline`: deterministic control branch
- `feature/poc-a-frontier-assisted`: frontier-assisted development branch

Operational note:

- The current repository is already on a stable PoC A baseline, so only `feature/poc-a-frontier-assisted` may need to be created operationally.
- The intended two-track model still remains baseline plus frontier, even if the current stable branch is `main`.

CODEX working rules for frontier development:

- Do not modify the baseline branch during frontier work
- Implement frontier changes only on `feature/poc-a-frontier-assisted`
- Preserve deterministic mode even on the frontier branch
- Add a mode switch rather than replacing deterministic logic
- Keep the same input contract, output contract, validation, trace, and evaluation structure
- Treat frontier behavior as a bounded judgment layer only
- Do not introduce memory, downstream action, or PoC B behavior

Merge policy:

- Baseline fixes may be cherry-picked or merged carefully into the frontier branch
- Frontier experiments do not flow back into baseline automatically
- Deterministic baseline behavior must remain reviewable and intact

Reference ADR:

- [ADR-0002-poc-a-frontier-branching-strategy.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0002-poc-a-frontier-branching-strategy.md)

## Triage Engine Selection

PoC A now includes a configurable triage engine seam so the same bounded workflow can run in deterministic or frontier-assisted mode without changing contracts or control layers.

- `TRIAGE_ENGINE` is the selector setting
- Allowed values are `deterministic` and `frontier`
- The default is `deterministic`
- Deterministic mode keeps the current control behavior unchanged
- Frontier mode is currently a stub path that is selectable and explicitly marked in trace/metadata, but it does not add provider integration or frontier inference yet
- The selected engine is surfaced in `run_metadata.triage_engine` and the execution trace
- Input contract, output contract, validation, trace, and evaluation structure remain the same across both modes

## PoC A-F Architecture Boundary

PoC A-F keeps deterministic layers in control of orchestration, contracts, validation, bounded repair, metadata, execution trace, evaluation assets, scoring/reporting structures, and guardrails/workflow control.

The frontier layer owns only bounded judgment generation for triage fields such as exception classification, reason summary, owner recommendation, priority, next actions, reviewer questions, and confidence.

PoC A-F frontier assistance is not autonomous workflow execution. It does not introduce cross-case memory, reuse of prior corrections, learning loops, autonomous routing, ERP posting, payment approval or rejection, outbound communications, uncontrolled tool usage, or PoC B learning behavior.

Reference ADR:

- [ADR-0003-poc-a-f-architectural-boundary.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0003-poc-a-f-architectural-boundary.md)

## PoC B Working Model

PoC B is a learning-oriented extension on top of the PoC A-F bounded triage baseline. It is not a rebuild and it does not replace the existing first-pass triage foundation.

- PoC A-F continues to own the bounded one-case-in / one-triage-out workflow, structured triage contract, human-review orientation, validation/control boundaries, bounded trace, and non-autonomous pilot posture
- PoC B will add reviewer outcome capture, reusable workflow memory, similar-case reuse, replay/evaluation memory, and measurable learning evidence in later stories
- PoC B must still preserve bounded triage, human review, and non-autonomous pilot boundaries
- CODEX must implement only the active story, must not pull future scope forward, and must preserve PoC A-F baseline behavior unless a story explicitly changes it

Reference ADR:

- [ADR-0004-poc-b-working-model.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0004-poc-b-working-model.md)

## PoC B Architectural Boundary

PoC B is a learning-oriented layer around the PoC A-F bounded triage foundation, not a replacement architecture.

- Deterministic and system-owned layers continue to own orchestration, contracts, validation, bounded repair, metadata, trace, and pilot control boundaries
- PoC B may add reviewer outcome capture, reusable memory, similar-case reuse, replay/evaluation memory, and learning-oriented observability later
- Human review remains mandatory and the AP analyst remains the final decision-maker during the pilot
- PoC B still excludes autonomous routing, payment action, ERP posting, silent auto-resolution, and unbounded cross-case agent behavior

Reference ADR:

- [ADR-0005-poc-b-architectural-boundary.md](/Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/docs/adr/ADR-0005-poc-b-architectural-boundary.md)

## Frontier Adapter Layer

PoC A-F now reserves a provider-agnostic frontier adapter layer so provider access stays outside business modules.

- The adapter layer owns provider-specific request/response handling only
- Business and orchestration modules must not call provider SDKs directly
- A stub adapter is available for safe local tests and non-provider runs
- An OpenAI adapter seam exists as the first concrete provider target without wiring live inference into the bounded workflow yet

## Frontier Provider Configuration

Frontier provider settings are externalized so later provider wiring can happen without code edits.

- `FRONTIER_PROVIDER` selects the frontier adapter provider and currently allows `stub` or `openai`
- `FRONTIER_MODEL` supplies the provider model identifier for frontier mode
- `FRONTIER_TIMEOUT_MS`, `FRONTIER_MAX_RETRIES`, `FRONTIER_TEMPERATURE`, and `FRONTIER_MAX_OUTPUT_TOKENS` use safe defaults when omitted
- `OPENAI_API_KEY` may be present for later OpenAI runs, but live credentials are not required for tests
- Deterministic mode does not require any frontier provider settings
- Frontier mode fails clearly when provider or model settings are missing or invalid

## Frontier Prompt Contract

PoC A-F now has a strict, versioned frontier triage prompt contract that packages normalized facts plus uncertainty signals into a provider-agnostic prompt payload.

- The prompt contract requires JSON-only output with the same bounded PoC A triage fields
- Allowed enum values for exception type, owner, priority, and confidence are embedded in the contract
- The prompt explicitly forbids unsupported claims, downstream action language, memory or cross-case references, and uncontrolled behavior
- The prompt builder is testable without live provider calls and is ready for later adapter wiring

## Frontier Trace Contract

Frontier runs emit concise bounded trace stages for prompt build, adapter call, output parsing, and frontier generation.

- Frontier trace notes stay short and operational
- Failure paths emit a failed stage at the relevant frontier step
- Trace does not include prompt bodies, full provider payloads, or hidden reasoning

## Shared Validation Reuse

After frontier output is parsed and normalized, it flows through the same shared PoC A schema validation and bounded repair layer used by deterministic runs.

- Validation status remains `valid`, `repaired_valid`, or `failed`
- Repair count and validation metadata stay comparable across deterministic and frontier engines
- Missing business content is not fabricated during repair

## Dual-Run Comparison

PoC A-F now includes a lightweight comparison runner that executes the same evaluation dataset cases in deterministic and frontier modes and stores side-by-side outputs in a reusable structure.

- Comparison records preserve `case_id` and `coverage_bucket`
- Deterministic and frontier outputs are kept as separate payloads for the same case
- Stub frontier mode works through the runner without live credentials
- The runner is intended for later scoring, metrics comparison, and demo preparation

## Frontier Demo Case Set

PoC A-F now includes a small four-case demo set for stakeholder walkthroughs. The selected cases are documented in `invoice_exception_poc_a/evaluation/frontier_demo_case_set.json`.

- `samples/sample_case.json` highlights a clean receiving mismatch happy path
- `invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json` shows an obvious missing-PO exception
- `invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json` is the best side-by-side ambiguity case
- `invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json` shows bounded low-information behavior
- Each entry includes the exact runnable path, why the case is included, and what the demo audience should notice

## Frontier Demo Script

PoC A-F also includes a stakeholder demo script in `invoice_exception_poc_a/evaluation/frontier_demo_script.md`.

- The script uses the same four F6.1 demo cases
- It explains deterministic versus frontier framing in business-safe language
- It includes per-case talk track guidance, comparison framing, and a closing takeaway
- It explicitly reinforces that frontier assistance is bounded and not autonomous workflow execution

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
