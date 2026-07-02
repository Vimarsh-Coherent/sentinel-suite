---
name: graphql-api
description: Design and build GraphQL APIs (schema, resolvers, queries/mutations/subscriptions). Use for GraphQL, schema, resolver, query, mutation, N+1, dataloader, Apollo, federation.
---

# GraphQL API Design

## When to use
Building or consuming a GraphQL API. Keywords: GraphQL, schema, resolver, query, mutation, subscription, N+1, Apollo.

## Design
- Model the **graph** around domain types + relationships, not endpoints.
- Queries (read), mutations (write), subscriptions (realtime).
- Version by **evolving** the schema (add fields, deprecate) rather than /v2.

## Performance
- **N+1 problem**: batch with a DataLoader. - Depth/complexity limiting to prevent abuse. - Persisted queries for known clients.

## Best practices
- Nullability is intentional. - Pagination via connections/cursors. - Errors as typed results where useful. - Authz in resolvers (per field if needed).

## Pitfalls
- N+1 queries. - Unbounded query depth (DoS). - Over-fetching in resolvers. - Leaking internal data through the graph.
