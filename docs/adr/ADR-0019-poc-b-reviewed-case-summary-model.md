# ADR-0019: PoC B Reviewed-Case Summary Model

## Status

Accepted

## Context

PoC B now has a reviewer outcome contract, minimum writeback contract, decision-memory schema, reviewer feedback capture flow, reviewed-outcome persistence, and writeback validation. The next bounded step is to represent previously reviewed cases in a concise, retrieval-friendly format that future similar-case stories can reuse without depending on raw traces or freeform notes.

This note and the associated schema define the bounded reviewed-case summary model only. This story does not implement similar-case retrieval behavior, replay execution, learning-metric aggregation, or autonomous workflow behavior.

## Decision

### Summary purpose

The reviewed-case summary model represents a concise, reusable, retrieval-friendly summary of a reviewed case that can later support similar-case reuse.

### Required bounded contents

At minimum, bounded reviewed-case summaries support:

- `normalized_case_pattern` for a concise normalized pattern of how the case was handled
- `final_disposition` for the final reviewed outcome and final routing disposition
- `override_reason_summary` for a bounded explanation of why an override happened, or a bounded accept-as-is indicator
- `routing_precedent` for concise routing precedent later stories may reuse
- `vendor_specific_notes` for concise vendor-scoped handling notes
- `confidence_hint` for bounded reliability or confidence context

### Decision-memory compatibility

The summary-building seam remains compatible with existing reviewed-outcome and decision-memory structures by deriving summaries from validated decision-memory records rather than inventing a competing reviewed-case shape.

### Retrieval-friendly principle

Reviewed-case summaries are:

- concise
- structured
- reusable
- free of raw chain-of-thought
- free of verbose raw trace dumps
- free of raw provider payloads

### Boundedness principle

This story adds a reviewed-case summary model and bounded summary-building seam only. It does not:

- execute retrieval behavior
- rank or fetch similar cases
- execute replay
- aggregate learning metrics
- create autonomous downstream behavior

## Consequences

- PoC B now has a stable concise reviewed-case representation for later similar-case reuse work.
- Future retrieval-oriented stories can reuse a bounded summary model instead of depending on raw traces or freeform notes.
