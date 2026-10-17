select
    'globex'::text                        as tenant_id,
    'globex:' || "Id"                     as deal_id,
    "Id"                                  as source_deal_id,
    'globex:' || "Partner_Account__c"     as partner_id,
    "Amount"::numeric(18, 2)              as amount_original,
    "CurrencyIsoCode"                     as currency_code,
    "StageName"                           as stage_raw,
    "CreatedDate"::timestamptz            as created_at,
    -- Careful: Salesforce fills CloseDate for open deals too (the *expected* date).
    -- It only becomes a real close date once the stage is won or lost (see int_deals).
    "CloseDate"::date::timestamptz        as close_date_raw
from {{ source('raw', 'globex_opportunities') }}
