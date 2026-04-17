# ADR-0003: PoC A-F Architectural Boundary

## Status

Accepted

## Context

PoC A-F extends the deterministic PoC A baseline with a frontier-assisted triage path. That extension must preserve the same bounded workflow, contracts, validation, trace, metadata, guardrails, and evaluation structure so frontier-assisted behavior can be compared cleanly against the control implementation.

Before provider integration begins, the repository needs an explicit architecture note that prevents drift. The frontier model is not the application. It is one bounded layer inside the application.

## Decision

Deterministic layers continue to own the application control surface for PoC A-F, including:

- orchestration
- input contract
- output contract
- schema validation
- bounded repair
- run metadata
- execution trace
- evaluation dataset
- scoring and reporting structures
- guardrails and workflow control

The frontier layer owns only bounded judgment generation for triage output fields. That bounded judgment generation may include:

- exception classification
- reason summary
- owner recommendation
- priority recommendation
- next actions
- reviewer questions
- confidence

Frontier assistance is therefore a bounded judgment layer, not autonomous workflow execution.

## Explicit Non-Goals

PoC A-F does not introduce:

- cross-case memory
- reuse of prior corrections
- learning loops
- autonomous routing
- ERP posting
- payment approval or rejection
- outbound communications
- uncontrolled tool usage
- PoC B learning behavior

## Consequences

- Deterministic layers remain responsible for enterprise-safe control boundaries.
- Frontier-assisted work can evolve without replacing orchestration, contracts, validation, metadata, trace, or reporting layers.
- Reviewers can assess frontier-assisted judgment quality while keeping the same bounded workflow and guardrails as the deterministic baseline.
