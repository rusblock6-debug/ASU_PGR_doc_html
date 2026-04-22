DROP VIEW IF EXISTS default.vehicle_telemetry_mv;
DROP TABLE IF EXISTS default.vehicle_telemetry;

INSERT INTO default.vehicle_telemetry
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
