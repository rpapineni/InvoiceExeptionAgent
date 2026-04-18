# ADR-0016: PoC B Reviewer Feedback Capture Flow

## Status

Accepted

## Context

PoC A-F already produces a bounded first-pass triage recommendation for human review. PoC B extends that workflow into a learning-oriented system where the reviewer feedback loop is mandatory because human corrections must become reusable product assets over time.

This note and the associated schema define the bounded reviewer feedback capture flow only. This story does not implement full decision-memory persistence orchestration, retrieval behavior, replay execution, learning-metric aggregation, or autonomous workflow behavior.

## Decision

The reviewer feedback capture flow records the structured result of human review after first-pass triage so later stories can write reusable reviewed-outcome intelligence safely and consistently.

### Required reviewer actions

At minimum, bounded reviewer feedback supports:

- `accept_as_is` for accepting the first-pass recommendation without changes
- `override_label` for a corrected outcome label when the reviewer changes the prediction
- `override_owner` for a corrected owner when the reviewer changes the routing outcome
- `reviewer_notes` for bounded analyst annotations
- `ambiguous_or_novel_flag` for bounded ambiguity or novelty signaling
- `precedent_usefulness_flag` for bounded indication that the reviewed case may be useful as precedent later

### Structured outcome compatibility

The captured feedback remains compatible with:

- the reviewer outcome contract through predicted-versus-final distinction and override semantics
- the minimum writeback contract through bounded preservation of reviewer annotations and corrected outcomes
- later decision-memory persistence through structured reviewed feedback payloads

### Human-control principle

The AP analyst remains the final decision-maker during the pilot. Feedback capture records human review; it does not authorize autonomous routing, payment action, or silent auto-resolution.

### Boundedness principle

Reviewer feedback capture remains bounded and implementation-safe. It does not:

- silently perform full decision-memory persistence orchestration
- perform retrieval behavior
- perform replay execution
- capture chain-of-thought or hidden reasoning
- create autonomous downstream behavior

## Consequences

- PoC B has a clear review-boundary flow for capturing structured human feedback after first-pass triage.
- Later stories can connect this bounded feedback payload to persistence or writeback flows without redefining reviewer actions or human control semantics.
