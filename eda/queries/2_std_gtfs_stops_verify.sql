SELECT
    stop_id
  , stop_code
  , stop_name
  , stop_desc
  , stop_lat
  , stop_lon
  , stop_url
  , location_type
  , parent_station
  , thoreb_id
  , source
  , snapshot_date
FROM db.standardized.gtfs_stops;

SELECT DISTINCT snapshot_date
FROM db.standardized.gtfs_stops;

SELECT count(*)
FROM db.standardized.gtfs_stops;

-- Duplicates by all columns
SELECT
    stop_id
  , stop_code
  , stop_name
  , stop_desc
  , stop_lat
  , stop_lon
  , stop_url
  , location_type
  , parent_station
  , thoreb_id
  , source
  , snapshot_date
  , count(*) AS duplicate_count
FROM db.standardized.gtfs_stops
GROUP BY ALL
HAVING count(*) > 1;
