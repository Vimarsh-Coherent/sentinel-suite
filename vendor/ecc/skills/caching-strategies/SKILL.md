---
name: caching-strategies
description: Add caching correctly to speed things up without serving stale data. Use for cache, caching, Redis cache, CDN, memoization, cache invalidation, TTL, cache-aside, stale data.
---

# Caching Strategies

## When to use
Reducing latency/load by reusing computed results. Keywords: cache, Redis, CDN, TTL, invalidation, memoize, stale.

## Patterns
- **Cache-aside** (most common): read cache → miss → load DB → populate cache.
- **Write-through / write-behind** for write-heavy paths.
- **CDN** for static assets; **HTTP caching** (ETag/Cache-Control) for responses.

## Invalidation (the hard part)
- Set a **TTL** as a safety net. - Invalidate on write (delete/update the key). - Use versioned keys to avoid stale reads. - Beware **thundering herd** (add jitter / lock on refill).

## Best practices
- Cache the expensive, frequently-read, rarely-changed. - Key includes all inputs. - Measure hit rate. - Never cache per-user data under a shared key.

## Pitfalls
- Stale data from missing invalidation. - Caching everything. - Cache stampede on expiry. - Leaking private data across users.
