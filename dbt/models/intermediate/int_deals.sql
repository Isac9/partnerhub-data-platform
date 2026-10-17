with deals as (
    select * from {{ ref('stg_acme__deals') }}
    union all
    select * from {{ ref('stg_globex__deals') }}
    union all
    select * from {{ ref('stg_initech__deals') }}
)

select
    d.tenant_id,
    d.deal_id,
    d.source_deal_id,
    d.partner_id,
    m.canonical_stage                                         as stage,
    case when m.canonical_stage in ('won', 'lost') then m.canonical_stage
         when m.canonical_stage is not null then 'open' end    as status,
    d.amount_original,
    d.currency_code,
    round(d.amount_original / fx.units_per_usd, 2)            as amount_usd,
    d.created_at,
    case when m.canonical_stage in ('won', 'lost') then d.close_date_raw end as closed_at,
    d.stage_raw
from deals d
left join {{ ref('stage_mapping') }} m
    on m.tenant_id = d.tenant_id and m.source_value = d.stage_raw
left join {{ ref('fx_rates') }} fx
    on fx.currency_code = d.currency_code
