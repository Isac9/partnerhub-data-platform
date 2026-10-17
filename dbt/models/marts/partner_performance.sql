select
    p.tenant_id,
    p.partner_id,
    p.partner_name,
    p.partner_type,
    p.country_code,
    count(d.deal_id)                                          as deals,
    count(d.deal_id) filter (where d.status = 'won')          as won,
    count(d.deal_id) filter (where d.status = 'lost')         as lost,
    count(d.deal_id) filter (where d.status = 'open')         as open,
    -- Win rate on closed deals only: open deals have no outcome yet.
    round(count(d.deal_id) filter (where d.status = 'won')::numeric
          / nullif(count(d.deal_id) filter (where d.status in ('won', 'lost')), 0), 3) as win_rate,
    coalesce(sum(d.amount_usd) filter (where d.status = 'won'), 0) as won_amount_usd
from {{ ref('dim_partners') }} p
left join {{ ref('fct_deals') }} d on d.partner_id = p.partner_id
group by 1, 2, 3, 4, 5
