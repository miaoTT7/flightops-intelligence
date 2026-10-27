with raw_lineage as (
    select source_file_id, source_row_number
    from {{ source('bts_raw', 'bts_on_time_performance') }}
),
staging_lineage as (
    select source_file_id, source_row_number
    from {{ ref('stg_bts_flights') }}
)
select
    coalesce(raw_lineage.source_file_id, staging_lineage.source_file_id) as source_file_id,
    coalesce(raw_lineage.source_row_number, staging_lineage.source_row_number) as source_row_number
from raw_lineage
full outer join staging_lineage
    using (source_file_id, source_row_number)
where raw_lineage.source_file_id is null
   or staging_lineage.source_file_id is null
