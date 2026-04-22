CREATE TABLE IF NOT EXISTS default.vehicle_telemetry
(
    bort Int32,
    timestamp UInt32,
    lat Float64,
    lon Float64,
    height Nullable(Float64),
    speed Nullable(Float64),
    fuel Nullable(Float64)
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(toDateTime(timestamp, 'UTC'))
ORDER BY (bort, timestamp);

CREATE MATERIALIZED VIEW IF NOT EXISTS default.vehicle_telemetry_mv
TO default.vehicle_telemetry
AS
SELECT
    toInt32OrZero(g.bort) AS bort,
    g.timestamp AS timestamp,
    g.lat AS lat,
    g.lon AS lon,
    g.height AS height,
    s.speed AS speed,
    f.fuel AS fuel
FROM default.gps_data AS g
LEFT JOIN
(
    SELECT
        vehicle_id,
        argMax(value, timestamp) AS speed
    FROM default.ekiper_events
    WHERE sensor_type = 'speed'
    GROUP BY vehicle_id
) AS s ON g.bort = s.vehicle_id
LEFT JOIN
(
    SELECT
        vehicle_id,
        argMax(value, timestamp) AS fuel
    FROM default.ekiper_events
    WHERE sensor_type = 'fuel'
    GROUP BY vehicle_id
) AS f ON g.bort = f.vehicle_id
WHERE toInt32OrZero(g.bort) != 0;
