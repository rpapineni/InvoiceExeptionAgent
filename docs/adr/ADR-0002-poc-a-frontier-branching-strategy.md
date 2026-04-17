# ADR-0002: PoC A Frontier Branching Strategy

## Status

Accepted

## Context

PoC A already serves as the deterministic control implementation. PoC A-F will be developed as a parallel frontier-assisted track so the same bounded workflow, contracts, validation, trace, and evaluation structures can be compared cleanly against the deterministic baseline.

The repository therefore needs a documented working model that keeps deterministic baseline work and frontier-assisted experimentation separate.

## Decision

The intended two-track branch model is:

- `release/poc-a-deterministic-baseline`
- `feature/poc-a-frontier-assisted`

Operational note:

- The current repository is already sitting on a stable PoC A baseline, so only `feature/poc-a-frontier-assisted` may need to be created operationally for day-to-day work.
- Even when the current stable branch is `main`, the documented baseline role is still `release/poc-a-deterministic-baseline` for handoff and comparison purposes.

## Branch Roles

- `release/poc-a-deterministic-baseline`: deterministic control implementation, stable comparison target, no frontier experimentation
- `feature/poc-a-frontier-assisted`: bounded frontier-assisted development track for PoC A-F

## Working Rules For Codex

- Do not modify the baseline branch during frontier work.
- Implement frontier changes only on `feature/poc-a-frontier-assisted`.
- Preserve the deterministic path even on the frontier branch.
- Add a mode switch rather than replacing deterministic logic.
- Keep the same input contract, output contract, validation, trace, and evaluation structure.
- Treat frontier behavior as a bounded judgment layer only.
- Do not introduce memory, downstream action, or PoC B behavior.

## Merge Policy

- Baseline fixes may be cherry-picked or merged carefully into the frontier branch when they preserve the bounded PoC A workflow.
- Frontier experiments do not flow back into the baseline automatically.
- Any move from frontier work back toward the deterministic baseline requires explicit review and deliberate selection of safe changes.

## Consequences

- Deterministic comparability is preserved.
- Frontier work can proceed without contaminating the PoC A control track.
- Reviewers can compare baseline and frontier behavior using the same contracts and evaluation scaffolding.
