# ADR-0012: PoC B Session Memory Boundary

## Status

Accepted

## Context

PoC A-F established a bounded one-case-in / one-triage-out workflow. PoC B extends that workflow into a learning-oriented system, but the memory model must remain explicitly layered so current-run continuity is not confused with reusable long-term workflow intelligence.

This note and the associated schema define the bounded session-memory boundary only. This story does not implement knowledge memory, decision memory, evaluation memory, retrieval, replay, reviewer writeback persistence, long-term storage, or autonomous workflow behavior.

## Decision

The PoC B session-memory boundary represents the bounded context required for the current in-flight run only. It is not reusable precedent memory and not generic conversation history.

### Required bounded contents

At minimum, bounded session memory supports:

- `case_context` for current-case context scoped to the active run
- `tool_outputs` for bounded tool-output records used during the current run
- `active_reasoning_state` for bounded current-run continuity without hidden reasoning or chain-of-thought capture
- `reviewer_session_state` for bounded reviewer-session continuity while human review is still in progress

### Lifetime and cleanup principle

Session memory is:

- scoped to the current run or active review session only
- ephemeral rather than reusable workflow intelligence
- subject to cleanup or reset at the end of the run or review session

### Separation principle

Session memory is distinct from:

- knowledge memory for policies, SOPs, and retrieval-friendly summaries
- decision memory for reviewed outcomes and reusable handling patterns
- evaluation memory for replay, regression, and benchmark artifacts

### Boundedness principle

Session memory remains bounded and implementation-safe. It does not:

- become generic chat-history accumulation
- silently become long-term precedent storage
- expose hidden reasoning or chain-of-thought
- imply similar-case reuse is already implemented

### Human-review principle

Session memory supports reviewer session continuity during an in-flight run, but it does not replace analyst judgment. The AP analyst remains the final decision-maker during the pilot.

## Consequences

- PoC B has a clear session-memory boundary for current-run continuity that matches the bounded pilot posture.
- Later stories can add separate knowledge, decision, and evaluation memory layers without overloading session memory with reusable storage semantics.
