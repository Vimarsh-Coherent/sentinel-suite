---
name: microservices-patterns
description: Design, split, and operate microservices. Use for microservices, service boundaries, inter-service communication, API gateway, service discovery, saga, distributed transactions, monolith to microservices.
---

# Microservices Patterns

## When to use
Splitting a system into services or operating them. Keywords: microservice, service boundary, gateway, saga, distributed.

## Boundaries
- Split by **business capability** (bounded context), not by layer.
- Each service owns its **own data** — no shared database.
- Start with a **modular monolith**; split only when a boundary is proven.

## Communication
- **Sync** (REST/gRPC) for request/response; **async** (events/queues) for decoupling.
- Use an **API gateway** for the edge; service discovery internally.

## Reliability
- Timeouts, retries with backoff, circuit breakers. - Idempotent handlers. - **Saga** pattern for distributed transactions (no 2PC). - Correlation IDs for tracing across services.

## Pitfalls
- Distributed monolith (services too chatty/coupled). - Shared DB. - No observability across services. - Splitting too early.
