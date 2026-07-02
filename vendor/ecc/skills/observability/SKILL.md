---
name: observability
description: Make systems debuggable in production with structured logging, metrics, and distributed tracing. Use for observability, logging, metrics, tracing, monitoring, alerting, Prometheus, OpenTelemetry, dashboards, SLO.
---

# Observability (Logs, Metrics, Traces)

## When to use
Understanding what a running system is doing. Keywords: logging, metrics, tracing, monitoring, alert, Prometheus, OpenTelemetry, SLO.

## The three pillars
1. **Logs** — structured (JSON), with context (request id, user id). Log events, not noise.
2. **Metrics** — counters/gauges/histograms (RED: Rate, Errors, Duration).
3. **Traces** — follow one request across services (correlation/trace id).

## Best practices
- Use a correlation id end-to-end. - Log at the right level; no secrets in logs. - Define **SLOs** and alert on symptoms (error rate, latency), not causes. - Dashboards for the golden signals. - Prefer OpenTelemetry for portability.

## Pitfalls
- Unstructured logs you can't query. - Alert fatigue (too many/noisy alerts). - Logging PII/secrets. - Metrics with unbounded label cardinality.
