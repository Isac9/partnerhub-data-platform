select deal_id, created_at, closed_at
from {{ ref('fct_deals') }}
where closed_at < created_at
