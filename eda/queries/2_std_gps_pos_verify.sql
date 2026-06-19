SELECT
    transport_type
  , line_number
  , vehicle_id
  , fleet_number
  , lat
  , lon
  , heading_deg
  , speed_kmh
  , floor_type
  , destination
  , snapshot_ts
  , snapshot_date
FROM
    db.standardized.gps_positions;

SELECT DISTINCT snapshot_date
FROM db.standardized.gps_positions;

SELECT DISTINCT snapshot_ts
FROM db.standardized.gps_positions
ORDER BY 1;
