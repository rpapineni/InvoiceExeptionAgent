# ADR-0001: PoC A Scope Guardrails

## Status

Accepted

## Context

PoC A is the bounded control version of the invoice exception pilot. Its goal is to demonstrate usefulness for first-pass triage of a single case without drifting into learning behavior, cross-case reuse, or downstream workflow automation.

Because later stories will add more implementation detail, the project needs explicit architectural boundaries now so future work does not accidentally introduce PoC B behavior or autonomous business actions.

## Decision

PoC A guardrails are enforced structurally in code and documentation:

- A dedicated guardrails policy module defines unsupported capabilities
- The orchestration path remains recommendation-only and surfaces the active guardrails in output
- Unsupported capabilities are blocked explicitly through a guardrail assertion API
- No prior-case retrieval, feedback persistence, cross-case memory, routing, approval, rejection, payment, or outbound communication path is added

The unsupported capability list for PoC A is:

- `prior_case_retrieval`
- `feedback_reuse`
- `autonomous_routing`
- `approve_action`
- `reject_action`
- `pay_action`
- `outbound_communication`
- `cross_case_memory`

## Consequences

Positive consequences:

- The PoC A boundary is visible in code, tests, and documentation
- Future stories have an explicit place to check scope before adding features
- Runtime callers can be failed fast if they attempt an out-of-scope action

Tradeoffs:

- The guardrails module adds structure before the related features exist
- Some future changes will require deliberate updates to the ADR, tests, and guardrail definitions rather than silent expansion

## Non-goals

This ADR does not add:

- reasoning logic
- memory
- feedback persistence
- downstream workflow execution
- PoC B learning features
