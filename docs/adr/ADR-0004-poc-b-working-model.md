# ADR-0004: PoC B Working Model and Baseline Preservation Strategy

## Status

Accepted

## Context

PoC A-F already provides the bounded frontier-assisted first-pass triage foundation for this repository. It preserves one-case-in / one-triage-out behavior, keeps human review in the loop, uses the same structured recommendation contract, and excludes autonomous downstream workflow behavior.

PoC B is not a fresh rebuild. It is a learning-oriented extension on top of PoC A-F. Before any PoC B implementation begins, the repository needs an explicit working model that makes baseline ownership, PoC B scope boundaries, and story-by-story implementation rules unambiguous.

## Decision

PoC A-F is the inherited baseline for PoC B. PoC B extends PoC A-F rather than replacing it.

PoC A-F continues to own the bounded first-pass triage foundation, including:

- one-case-in / one-triage-out bounded workflow
- structured triage recommendation contract
- human-review orientation
- bounded execution trace
- validation and control boundaries
- non-autonomous pilot posture

PoC B will add learning-oriented capabilities around that foundation later, including:

- reviewer outcome capture
- reusable workflow memory
- similar-case and prior-pattern reuse
- replay and evaluation memory
- measurable learning evidence

PoC B must still preserve the same bounded human-in-the-loop control posture as PoC A-F. It remains a pilot extension inside a governed workflow, not autonomous workflow execution.

## Explicit Non-Goals For This Working Model

This working model does not introduce:

- memory implementation
- feedback capture implementation
- writeback behavior
- retrieval behavior
- replay behavior
- business-logic changes
- input or output contract changes
- autonomous routing
- payment action
- ERP posting
- silent auto-resolution of ambiguous cases
- unbounded cross-case agent behavior

## CODEX Working Rules For PoC B

- Implement only the active story and nothing beyond it.
- Do not pull future scope forward.
- Preserve PoC A-F baseline behavior unless the active story explicitly changes it.
- Return evidence against each acceptance criterion.
- Deliver PoC B one story at a time, with review between stories.
- Preserve bounded triage, human review, and non-autonomous pilot boundaries throughout PoC B work.

## Consequences

- PoC A-F remains the stable bounded triage baseline.
- PoC B work can evolve as a disciplined extension without drifting into autonomous workflow behavior.
- Reviewers can assess PoC B learning-oriented additions incrementally while preserving the same enterprise-safe control posture and baseline comparability.
