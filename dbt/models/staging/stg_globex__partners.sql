select
    'globex'::text         as tenant_id,
    'globex:' || "Id"      as partner_id,
    "Id"                   as source_partner_id,
    "Name"                 as partner_name,
    "Email__c_hash"        as contact_key,
    "Email__c_domain"      as email_domain,
    "Type"                 as partner_type_raw,
    "BillingCountry"       as country_raw
from {{ source('raw', 'globex_partner_accounts') }}
