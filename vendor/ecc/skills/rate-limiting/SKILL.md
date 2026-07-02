---
name: rate-limiting
description: Protect APIs and services from overload and abuse with rate limiting. Use for rate limit, throttle, 429, token bucket, leaky bucket, quota, abuse protection, backpressure.
---

# Rate Limiting & Throttling

## When to use
Limiting how often a client can call something. Keywords: rate limit, throttle, 429, quota, token bucket, abuse.

## Algorithms
- **Token bucket** — allows bursts up to a cap, refills over time (most common).
- **Leaky bucket** — smooths to a steady rate.
- **Fixed / sliding window** counters — simple, watch boundary bursts.

## Best practices
- Key by user/API-key/IP as appropriate. - Return **429** with `Retry-After` and `RateLimit-*` headers. - Use a shared store (Redis) for distributed limits. - Different tiers/limits per plan. - Fail open vs closed — decide deliberately.

## Pitfalls
- Per-instance limits in a cluster (bypassed by load balancing). - No headers → clients can't back off. - Limiting legit bursts too aggressively.
