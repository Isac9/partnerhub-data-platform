with partners as (
    select * from {{ ref('stg_acme__partners') }}
    union all
    select * from {{ ref('stg_globex__partners') }}
    union all
    select * from {{ ref('stg_initech__partners') }}
)

-- Left joins on purpose: an unknown value stays visible as a null, and the not_null tests catch it.
select
    p.tenant_id,
    p.partner_id,
    p.source_partner_id,
    p.partner_name,
    t.canonical_partner_type   as partner_type,
    c.country_code,
    p.email_domain,
    p.contact_key,
    p.partner_type_raw,
    p.country_raw
from partners p
left join {{ ref('partner_type_mapping') }} t
    on t.tenant_id = p.tenant_id and t.source_value = p.partner_type_raw
left join {{ ref('country_mapping') }} c
    on c.source_value = p.country_raw
