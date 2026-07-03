-- ===============================================================================================
-- Raw GPS data: STANDARDIZED -> STANDARDIZED
-- Filter `transport_type == 2` and `line_number == "8"`. Drop all other vehicles.
-- ===============================================================================================

CREATE OR REPLACE TABLE standardized.route8_positions AS
SELECT
    gp.transport_type
  , gp.line_number
  , gp.vehicle_id
  , gp.fleet_number
  , gp.lat
  , gp.lon
  , gp.heading_deg
  , gp.speed_kmh
  , gp.floor_type
  , gp.destination
  , source
  , gp.snapshot_ts
  , gp.snapshot_date
FROM db.standardized.gps_positions AS gp
WHERE
    gp.transport_type = 2
    AND gp.line_number = '8'
    AND lower(destination) = 'äigrumäe'
    --AND fleet_number = 35
   ;
