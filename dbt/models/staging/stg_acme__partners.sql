select
    'acme'::text           as tenant_id,
    'acme:' || id          as partner_id,
    id                     as source_partner_id,
    name                   as partner_name,
    contact_email_hash     as contact_key,
    contact_email_domain   as email_domain,
    partner_type           as partner_type_raw,
    country                as country_raw
from {{ source('raw', 'acme_companies') }}
