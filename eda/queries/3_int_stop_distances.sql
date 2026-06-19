-- How far was each route 8 bus from Zoo and Toompark at each moment?
-- Rita works in RMK Tallinn office. She takes the Tallinn city bus number 8 from Zoo to Toompark (names of bus stops) to get to work.

-- Zoo stop_id = 822
-- Toompark stop_id = 1769



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
FROM db.standardized.gtfs_stops
WHERE lower(stop_name) = 'toompark';
