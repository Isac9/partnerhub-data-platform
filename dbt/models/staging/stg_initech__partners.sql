select
    'initech'::text        as tenant_id,
    'initech:' || id       as partner_id,
    id                     as source_partner_id,
    name                   as partner_name,
    email_hash             as contact_key,
    email_domain           as email_domain,
    label                  as partner_type_raw,
    address_country        as country_raw
from {{ source('raw', 'initech_organizations') }}
