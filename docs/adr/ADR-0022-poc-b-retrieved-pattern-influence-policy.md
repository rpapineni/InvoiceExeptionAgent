# ADR-0022: PoC B Retrieved-Pattern Influence Policy

## Status

Accepted

## Context

PoC B now has reviewed-case summaries, a similar-case retrieval contract, and a vendor exception profile model. Before any future retrieval-oriented story is allowed to shape recommendation output, PoC B needs a bounded influence policy that defines what retrieved artifacts may influence, what they may not influence, and how that influence remains traceable and human-review-centered.

This note and the associated schema define the bounded retrieved-pattern influence policy only. This story does not implement live retrieval execution, ranking or scoring, replay execution, learning-metric aggregation, or autonomous workflow behavior.

## Decision

### Influence-policy purpose

The retrieved-pattern influence policy defines how retrieved patterns may influence future outputs in bounded ways. It does not grant retrieved artifacts independent authority.

### Allowed influence targets

At minimum, bounded retrieved-pattern influence supports:

- `recommendation_influence`
- `explanation_influence`
- `confidence_influence`
- `next_actions_influence`
- `reviewer_questions_influence`

### Source compatibility

The influence policy remains compatible with retrievable source types already defined in PoC B, including:

- reviewed-case summaries
- policy snippets
- vendor patterns
- routing precedents

### Non-authority principle

Retrieved artifacts:

- do not override reviewed truth
- do not bypass human review
- do not silently auto-resolve cases
- do not authorize routing or payment action on their own

### Traceability principle

Retrieved-pattern influence must remain traceable. The bounded policy representation records what type of artifact influenced the output, what bounded part of the output it was allowed to influence, and preserves an explicit trace string rather than opaque hidden influence.

### Boundedness principle

The retrieved-pattern influence seam remains bounded and implementation-safe. It does not:

- perform live retrieval
- rank or fetch retrieved artifacts
- expose chain-of-thought
- expose raw provider dumps
- become hidden reasoning-by-proxy
- imply autonomous authority

### Human-review principle

The AP analyst remains the final decision-maker. Retrieved patterns are reviewer-support context only and do not replace human judgment.

## Consequences

- PoC B now has a stable advisory-only contract for how retrieved patterns may shape recommendation-related output.
- Later retrieval stories can plug into a bounded influence policy without redefining authority, traceability, or human-review rules.
