---
name: event-driven-messaging
description: Build asynchronous, event-driven systems with message queues and brokers (Kafka, RabbitMQ, SQS, Redis Streams). Use for queues, pub/sub, events, producers/consumers, at-least-once delivery, dead-letter queues.
---

# Event-Driven Messaging

## When to use
Decoupling producers/consumers or async processing. Keywords: queue, Kafka, RabbitMQ, pub/sub, event, consumer, broker.

## Concepts
- **Producer** publishes events; **consumer** subscribes. The broker decouples them in time.
- **Delivery**: at-least-once is common → make consumers **idempotent**.
- **Ordering**: only guaranteed within a partition/queue.

## Best practices
- Design events as **facts** ("OrderPlaced"), not commands. - Include a schema/version + event id + timestamp. - **Dead-letter queue** for poison messages. - Backpressure: cap concurrency; ack only after success. - Make consumers idempotent (dedupe by event id).

## Pitfalls
- Assuming exactly-once. - No DLQ → infinite retries. - Giant events / chatty topics. - Losing ordering assumptions.
