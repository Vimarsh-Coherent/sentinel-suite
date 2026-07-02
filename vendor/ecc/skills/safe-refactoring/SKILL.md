---
name: safe-refactoring
description: Improve code structure without changing behavior. Use for refactor, clean up code, reduce duplication, extract function, rename, simplify, improve readability, tech debt cleanup.
---

# Safe Refactoring

## When to use
Restructuring working code. Keywords: refactor, clean up, extract, rename, simplify, DRY, reduce complexity.

## Golden rule
**Never refactor without tests.** Tests are the safety net that prove behavior didn't change.

## Steps
1. Ensure the code is covered by tests (write characterization tests first if not).
2. Make **one small change** at a time; run tests after each.
3. Common moves: extract function/variable, inline, rename for clarity, replace conditionals with polymorphism, remove duplication.
4. Commit each green step separately.

## Signals to refactor
Long functions, deep nesting, duplicated blocks, unclear names, comments explaining "what" (not "why"), a class doing too much.

## Pitfalls
- Refactoring + adding features in the same commit. - No tests → silent behavior change. - Big-bang rewrites. - Over-abstracting (premature generalization).
