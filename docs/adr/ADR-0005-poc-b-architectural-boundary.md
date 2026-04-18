# ADR-0005: PoC B Architectural Boundary and Non-Goals

## Status

Accepted

## Context

PoC A-F already provides the bounded first-pass triage foundation for this repository. It preserves the one-case-in / one-triage-out workflow, structured reviewer-oriented recommendation output, bounded validation and repair behavior, metadata, execution trace, and a non-autonomous pilot posture.

PoC B extends that foundation with learning-oriented capabilities, but it must not replace the existing control architecture or drift into autonomous workflow execution. Before implementation continues, the repository needs an explicit architectural boundary note that separates inherited PoC A-F responsibilities from the new PoC B learning layer.

## Decision

PoC A-F remains the bounded triage foundation. PoC B is a learning-oriented layer around that foundation, not a replacement for it.

### Inherited PoC A-F foundation responsibilities

Deterministic and system-owned layers continue to own:

- one-case-in / one-triage-out bounded triage flow
- reviewer-oriented structured recommendation contract
- orchestration
- input and output contracts
- validation and bounded repair behavior
- metadata and bounded trace posture
- pilot control boundaries
- non-autonomous workflow posture

### PoC B learning-layer responsibilities added later

PoC B may add later:

- reviewer outcome capture after triage
- reusable workflow memory
- decision memory for reviewed outcomes
- knowledge memory for retrieval-oriented context
- evaluation memory for replay and regression
- similar-case reuse
- learning-oriented observability and improvement evidence

### Human control principle

The AP analyst remains in control of the final handling decision during this pilot. PoC B remains review-centered and does not replace analyst judgment.

## Explicit Non-Goals

PoC B still does not introduce:

- autonomous routing
- payment action
- ERP posting
- outbound financial execution
- silent auto-resolution of ambiguous cases
- unbounded cross-case agent behavior
- open-ended tool orchestration beyond bounded pilot scope

## Consequences

- PoC A-F remains the stable control foundation for bounded first-pass triage.
- PoC B can evolve as a learning-oriented layer without replacing orchestration, contracts, validation, metadata, trace, or pilot control boundaries.
- Human review remains mandatory and the final handling decision stays with the AP analyst throughout the pilot.
