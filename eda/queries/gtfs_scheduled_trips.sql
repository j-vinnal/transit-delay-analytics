SELECT
    r.route_id
  , r.route_short_name
  , r.route_long_name
  , t.service_id
  , t.trip_id
  , t.trip_headsign
  , c.monday
  , c.tuesday
  , c.wednesday
  , c.thursday
  , c.friday
  , c.saturday
  , c.sunday
  , c.start_date
  , c.end_date
    -- Zoo (stop_id = 822)
  , max(st.arrival_time) FILTER (WHERE st.stop_id = 822)::TIME AS arrival_time_zoo
  , max(st.departure_time) FILTER (WHERE st.stop_id = 822)::TIME AS departure_time_zoo
    -- Toompark (stop_id = 1769)
  , max(st.arrival_time) FILTER (WHERE st.stop_id = 1769)::TIME AS arrival_time_toompark
  , max(st.departure_time) FILTER (WHERE st.stop_id = 1769)::TIME AS toompark_departure_toompark
  -- Travel time from the Zoo departure to the Toompark arrival
  , strptime(max(st.arrival_time) FILTER (WHERE st.stop_id = 1769), '%H:%M:%S')
    - strptime(max(st.departure_time) FILTER (WHERE st.stop_id = 822), '%H:%M:%S') AS travel_duration
FROM standardized.gtfs_routes AS r
INNER JOIN standardized.gtfs_trips AS t
    ON  r.route_id = t.route_id
        AND lower(t.trip_headsign) = 'äigrumäe'
INNER JOIN standardized.gtfs_stops_times AS st
    ON  t.trip_id = st.trip_id
        AND st.stop_id IN (822, 1769)
INNER JOIN standardized.gtfs_calendar AS c
    ON  t.service_id = c.service_id
        AND c.monday = 1
        AND c.tuesday = 1
        AND c.wednesday = 1
        AND c.thursday = 1
        AND c.friday = 1
--INNER JOIN standardized.gtfs_stops AS s ON st.stop_id = s.stop_id
WHERE r.route_short_name = '8'
GROUP BY
    r.route_id
  , r.route_short_name
  , r.route_long_name
  , t.service_id
  , t.trip_id
  , t.trip_headsign
  , c.monday
  , c.tuesday
  , c.wednesday
  , c.thursday
  , c.friday
  , c.saturday
  , c.sunday
  , c.start_date
  , c.end_date
ORDER BY t.trip_id, arrival_time_zoo;
--LIMIT 10;
