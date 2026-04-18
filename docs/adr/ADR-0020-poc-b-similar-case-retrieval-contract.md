# ADR-0020: PoC B Similar-Case Retrieval Contract

## Status

Accepted

## Context

PoC B already has reviewed outcomes persisted into decision memory, writeback validation and auditability, and reviewed-case summaries that are concise and retrieval-friendly. The next bounded step is to define what kinds of reusable artifacts may later be fetched and how those artifacts are represented without implementing live retrieval.

This note and the associated schema define the bounded similar-case retrieval contract only. This story does not implement live retrieval execution, ranking or scoring logic, replay execution, learning-metric aggregation, or autonomous workflow behavior.

## Decision

### Retrieval contract purpose

The similar-case retrieval contract defines the bounded structure for what may be retrieved later to support future case handling. It does not perform live retrieval in this story.

### Supported retrievable source types

At minimum, bounded retrieval artifacts support:

- `reviewed_case_summary`
- `policy_snippet`
- `vendor_pattern`
- `routing_precedent`

### Retrieval-contract fields

At minimum, bounded retrieval artifacts support:

- `retrieval_scope`
- `source_type`
- `source_ref`
- `source_summary`
- `relevance_hint`

Optional bounded fields may also be used where helpful:

- `vendor_ref`
- `policy_ref`
- `precedent_ref`
- `retrieval_layer`

### Compatibility principle

The retrieval contract remains compatible with:

- knowledge-memory artifacts for policies, SOPs, playbooks, routing guidance, and reviewed-case summaries
- decision-memory artifacts for vendor patterns, routing tendencies, and reviewed reviewed-outcome intelligence
- reviewed-case summaries as concise retrieval-friendly records

### Boundedness principle

The retrieval contract remains bounded and implementation-safe. It does not:

- execute retrieval
- rank results
- imply live retrieval is already implemented
- expose chain-of-thought
- expose raw provider dumps
- become open-ended context stuffing

### Human-review principle

Retrieved artifacts are bounded context only. They do not carry autonomous authority and remain consistent with PoC B's human-review-centered posture.

## Consequences

- PoC B now has a stable contract for future similar-case retrieval work.
- Later stories can build fetch or ranking behavior on top of a bounded retrieval-artifact shape instead of inventing a new one.
