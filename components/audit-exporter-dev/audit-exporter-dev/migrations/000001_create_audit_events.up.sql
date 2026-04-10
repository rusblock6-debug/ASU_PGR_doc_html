CREATE DATABASE IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.audit_events
(
    source_name  LowCardinality(String),
    outbox_id    UUID,
    entity_type  LowCardinality(String),
    entity_id    String,
    operation    LowCardinality(String),
    old_values   Nullable(String),
    new_values   Nullable(String),
    user_id      Nullable(String),
    timestamp    DateTime,
    service_name LowCardinality(String)
)
ENGINE = MergeTree()
ORDER BY (source_name, outbox_id)
SETTINGS non_replicated_deduplication_window = 1000;
