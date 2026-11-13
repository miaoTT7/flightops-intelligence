select 'rotation_row_count_mismatch' as failure_reason
where (select count(*) from {{ ref('int_aircraft_rotation_pairing') }})
   <> (select count(*) from {{ ref('int_flight_timestamps') }})

