CREATE TABLE IF NOT EXISTS default.gps_data
(
    bort LowCardinality(String),
    timestamp UInt32,
    height Nullable(Float64),
    lat Float64,
    lon Float64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(toDateTime(timestamp, 'UTC'))
ORDER BY (bort, timestamp);
