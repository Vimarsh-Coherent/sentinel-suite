---
name: infrastructure-as-code
description: Provision and manage cloud infrastructure declaratively with Terraform / Pulumi / CloudFormation. Use for terraform, IaC, provisioning servers, state management, modules, plan/apply, drift detection.
---

# Infrastructure as Code

## When to use
Creating/changing cloud resources in code. Keywords: terraform, IaC, provision, plan, apply, state, module, drift.

## Principles
- **Declarative** — describe desired state, let the tool reconcile.
- **Idempotent** — running twice changes nothing new.
- **Version-controlled** — infra changes go through PRs like code.

## Workflow
1. `plan` — preview changes; review the diff before applying.
2. `apply` — make changes; store **state** remotely (locked).
3. Use **modules** for reusable components; keep environments (dev/stage/prod) separate.

## Best practices
- Remote, locked state (S3+DynamoDB / Terraform Cloud). - Never edit infra by hand (causes drift). - Least-privilege IAM. - Tag everything. - `plan` in CI on PRs, `apply` on merge.

## Pitfalls
- Local state files committed to git. - Secrets in `.tfvars` in the repo. - Giant monolithic state. - Manual console changes → drift.
