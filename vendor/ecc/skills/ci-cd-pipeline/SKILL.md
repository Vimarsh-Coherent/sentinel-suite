---
name: ci-cd-pipeline
description: Design and troubleshoot continuous integration / delivery pipelines (GitHub Actions, GitLab CI, CircleCI). Use for build/test/deploy automation, pipeline YAML, caching, matrix builds, secrets in CI, release automation.
---

# CI/CD Pipeline

## When to use
Setting up or fixing automated build/test/deploy. Keywords: CI, CD, GitHub Actions, workflow, pipeline, deploy on push, release automation.

## Core stages
1. **Trigger** — on push / PR / tag / schedule.
2. **Build** — install deps (cache them), compile.
3. **Test** — unit + lint + type-check; fail fast.
4. **Security** — secret scan + dependency audit.
5. **Deploy** — only from the main branch / tags; use environments + approvals.

## Best practices
- Cache dependencies (keyed on the lockfile hash) to speed runs.
- Run jobs in a **matrix** across OS/versions when it matters.
- Keep secrets in the CI secret store, never in YAML.
- Make the pipeline **reproducible locally** (same commands).
- Fail the build on lint/type/test errors — no "allow failure".

## Common pitfalls
- Slow pipelines from no caching. - Deploying from feature branches. - Secrets echoed in logs. - Flaky tests left as "retry".
