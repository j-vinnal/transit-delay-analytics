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
  , source
  , snapshot_ts
  , snapshot_date
FROM db.standardized.route8_positions;

SELECT count(*) FROM db.standardized.route8_positions;
--2242

-- Sama vehicle_id on seotud mitme fleet_number mõnel üksikul juhul
SELECT
    vehicle_id
    , destination
  , count(DISTINCT fleet_number) AS fleet_number_count
FROM db.standardized.route8_positions
GROUP BY vehicle_id, destination
HAVING count(DISTINCT fleet_number) > 1;

-- Duplicates by all columns
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
  , source
  , snapshot_ts
  , snapshot_date
  , count(*) AS duplicate_count
FROM db.standardized.route8_positions
GROUP BY ALL
HAVING count(*) > 1;
-- 0
