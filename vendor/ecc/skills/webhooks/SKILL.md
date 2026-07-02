---
name: webhooks
description: Design outgoing webhooks and safely consume incoming ones. Use for webhook, callback URL, signature verification, retries, idempotency, Stripe/GitHub webhooks, event delivery.
---

# Webhooks (Build & Consume)

## When to use
Sending or receiving HTTP event callbacks. Keywords: webhook, callback, signature, delivery, retry, idempotency.

## Consuming (incoming)
- **Verify the signature** (HMAC) before trusting the payload. - Respond **2xx fast**; process async. - Be **idempotent** (dedupe by event id — providers retry). - Validate + allowlist event types.

## Producing (outgoing)
- Sign payloads (HMAC with a per-subscriber secret). - **Retry** with exponential backoff on non-2xx; give up after N with a dead-letter. - Include event id, type, timestamp, version. - Let users see delivery logs + re-send.

## Pitfalls
- Trusting unsigned payloads. - Doing heavy work in the request (timeouts → retries → duplicates). - No idempotency → double processing. - No retry/backoff.
