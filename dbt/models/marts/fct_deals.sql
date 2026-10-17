select
    deal_id,
    tenant_id,
    partner_id,
    source_deal_id,
    stage,
    status,
    amount_original,
    currency_code,
    amount_usd,
    created_at,
    closed_at,
    -- Days open: until the close date, or until the reporting date for deals still open.
    round((extract(epoch from coalesce(closed_at, '{{ var("as_of") }}'::timestamptz) - created_at) / 86400)::numeric, 1)
                       as duration_days,
    status = 'open'    as is_censored
from {{ ref('int_deals') }}
