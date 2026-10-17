select
    'acme'::text                    as tenant_id,
    'acme:' || id                   as deal_id,
    id                              as source_deal_id,
    'acme:' || partner_company_id   as partner_id,
    amount::numeric(18, 2)          as amount_original,
    deal_currency_code              as currency_code,
    dealstage                       as stage_raw,
    createdate::timestamptz         as created_at,
    closedate::timestamptz          as close_date_raw
from {{ source('raw', 'acme_deals') }}
