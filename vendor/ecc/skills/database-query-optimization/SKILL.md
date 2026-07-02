---
name: database-query-optimization
description: Diagnose and speed up slow database queries with indexes and query tuning. Use for slow query, database index, EXPLAIN, query plan, N+1, full table scan, optimize SQL, database performance.
---

# Database Query Optimization

## When to use
A query/page is slow because of the database. Keywords: slow query, index, EXPLAIN, query plan, N+1, table scan, optimize SQL.

## Process
1. **Measure** — find the slow query (slow query log / APM).
2. **EXPLAIN** — read the plan; look for full table scans, big row estimates, missing index usage.
3. **Index** the columns in WHERE/JOIN/ORDER BY (composite index order matters: equality → range).
4. **Re-measure**.

## Best practices
- Select only needed columns (avoid `SELECT *`). - Fix **N+1** with joins / eager loading / batching. - Paginate with keyset (seek) not large OFFSET. - Watch index write-cost; don't over-index. - Use covering indexes for hot reads.

## Pitfalls
- Adding indexes blindly (slows writes). - Functions on indexed columns (kills index use). - Huge OFFSET pagination. - Ignoring the query plan.
