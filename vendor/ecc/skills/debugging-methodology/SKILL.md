---
name: debugging-methodology
description: A systematic approach to finding and fixing bugs. Use for debugging, 'why is this failing', reproduce a bug, root cause analysis, stack traces, unexpected behavior, it works locally but not in prod.
---

# Debugging Methodology

## When to use
Any "it's broken and I don't know why". Keywords: debug, bug, crash, error, root cause, reproduce, stack trace.

## The loop
1. **Reproduce** reliably — smallest input that triggers it.
2. **Observe** — read the actual error/stack trace fully; add logging around the failure.
3. **Hypothesize** — form ONE testable guess about the cause.
4. **Isolate** — bisect (comment out halves / `git bisect`) to narrow the location.
5. **Fix** the root cause, not the symptom.
6. **Verify** — the repro now passes; add a regression test.

## Techniques
- Rubber-duck the code path out loud. - Diff a working vs broken state. - Check assumptions with asserts/prints. - Read the docs of the exact function. - Binary-search the commit history (`git bisect`).

## Pitfalls
- Fixing symptoms (adding a null check without asking why it's null). - Changing many things at once. - Not writing a regression test after.
