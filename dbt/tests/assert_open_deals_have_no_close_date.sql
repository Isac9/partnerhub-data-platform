-- Salesforce fills CloseDate on open deals (expected date). It must not leak into closed_at.
select deal_id, status, closed_at
from {{ ref('fct_deals') }}
where (status = 'open' and closed_at is not null)
   or (status in ('won', 'lost') and closed_at is null)
