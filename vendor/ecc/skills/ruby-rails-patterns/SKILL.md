---
name: ruby-rails-patterns
description: Idiomatic Ruby and Ruby on Rails development. Use for Ruby, Rails, ActiveRecord, migrations, controllers, models, RSpec, gems, Sidekiq, Rails conventions.
---

# Ruby on Rails Patterns

## When to use
Working in a Ruby/Rails codebase. Keywords: Ruby, Rails, ActiveRecord, migration, controller, model, RSpec, gem, Sidekiq.

## Conventions
- **Convention over configuration** — follow Rails naming (models singular, tables plural).
- Fat models / skinny controllers, but extract to **service objects** / POROs when models bloat.
- Use **strong parameters**; never mass-assign untrusted input.

## Data
- Migrations are versioned + reversible. - Avoid N+1 with `includes`. - Add DB indexes for foreign keys and lookups.

## Testing / jobs
- **RSpec** (or Minitest); test models, requests, and system specs. - Background work via **Sidekiq/ActiveJob** (idempotent jobs).

## Pitfalls
- N+1 queries. - Callback soup in models. - Business logic in controllers. - Skipping strong params (mass-assignment risk).
