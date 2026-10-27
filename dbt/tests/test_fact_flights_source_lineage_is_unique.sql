select
    source_file_id,
    source_row_number,
    count(*) as record_count
from {{ ref('fact_flights') }}
group by source_file_id, source_row_number
having count(*) <> 1
