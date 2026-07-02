---
name: feature-flags
description: Ship code safely behind toggles and roll out gradually. Use for feature flag, feature toggle, gradual rollout, A/B test, kill switch, canary, dark launch.
---

# Feature Flags

## When to use
Decoupling deploy from release, gradual rollouts, experiments. Keywords: feature flag, toggle, rollout, A/B, kill switch, canary.

## Flag types
- **Release** (turn a feature on/off), **experiment** (A/B), **ops** (kill switch), **permission** (per plan/user).

## Best practices
- Default **off**; roll out to % of users, then ramp. - Keep a **kill switch** for risky features. - Evaluate flags server-side for security-sensitive gates. - **Clean up** stale flags (they become tech debt). - Log which variant a user got.

## Pitfalls
- Flags living forever (flag debt). - Nested flags → combinatorial complexity. - Client-side flags for security decisions. - No cleanup plan.
