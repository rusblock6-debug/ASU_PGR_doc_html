CREATE TABLE IF NOT EXISTS default.ekiper_events
(
    status LowCardinality(String),
    value Float64,
    vehicle_id String,
    sensor_type LowCardinality(String),
    timestamp UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(toDateTime(timestamp, 'UTC'))
ORDER BY (vehicle_id, timestamp);

CREATE TABLE IF NOT EXISTS default.s3_file
(
    object_key   String,
    etag         String,
    loaded_at    DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(loaded_at)
ORDER BY (object_key, etag);
