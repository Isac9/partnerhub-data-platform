-- Every deal counted in the source must be in the warehouse, with the same total amount.
-- A mapping that silently drops rows would fail here.
with source as (
    select tenant_id, row_count, amount_total
    from {{ source('audit', 'source_totals') }}
    where run_id = (select max(run_id) from {{ source('audit', 'source_totals') }})
),

warehouse as (
    select tenant_id, count(*) as row_count, sum(amount_original) as amount_total
    from {{ ref('fct_deals') }}
    group by tenant_id
)

select
    coalesce(s.tenant_id, w.tenant_id) as tenant_id,
    s.row_count    as source_rows,
    w.row_count    as warehouse_rows,
    s.amount_total as source_amount,
    w.amount_total as warehouse_amount
from source s
full outer join warehouse w on w.tenant_id = s.tenant_id
where coalesce(s.row_count, -1) <> coalesce(w.row_count, -1)
   or abs(coalesce(s.amount_total, 0) - coalesce(w.amount_total, 0)) > 0.01
