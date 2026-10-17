select
    partner_id,
    tenant_id,
    source_partner_id,
    partner_name,
    partner_type,
    country_code,
    email_domain,
    contact_key
from {{ ref('int_partners') }}
