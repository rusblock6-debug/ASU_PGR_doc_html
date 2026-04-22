CREATE TABLE IF NOT EXISTS default.cycle_tag_history
(
    id String,
    timestamp DateTime('UTC'),
    vehicle_id Int32,
    cycle_id Nullable(String),
    place_id Int32,
    place_name String,
    place_type LowCardinality(String),
    tag_id Int32,
    tag_name String,
    tag_event Enum8('entry' = 1, 'exit' = 2) DEFAULT 'entry'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (vehicle_id, timestamp);
