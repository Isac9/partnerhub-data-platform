select
    'initech'::text                                   as tenant_id,
    'initech:' || id                                  as deal_id,
    id                                                as source_deal_id,
    'initech:' || org_id                              as partner_id,
    value::numeric(18, 2)                             as amount_original,
    currency                                          as currency_code,
    -- Pipedrive keeps status and pipeline step apart: open deals are mapped per step.
    case when status = 'open' then 'open:' || stage_id else status end as stage_raw,
    add_time::timestamp at time zone 'UTC'            as created_at,
    close_time::timestamp at time zone 'UTC'          as close_date_raw
from {{ source('raw', 'initech_deals') }}
