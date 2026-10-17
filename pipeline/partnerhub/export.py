"""Analysis datasets: marts exported to Parquet, then queried with DuckDB."""
from decimal import Decimal

import duckdb
import pandas as pd

from .config import EXPORT_DIR

TABLES = ["fct_deals", "dim_partners", "partner_performance"]

# Look at the distribution before trusting an average: deal sizes are heavily skewed.
DISTRIBUTION_SQL = """
select tenant_id,
       count(*)                              as won_deals,
       round(avg(amount_usd))                as mean_usd,
       round(median(amount_usd))             as median_usd,
       round(quantile_cont(amount_usd, 0.9)) as p90_usd,
       round(max(amount_usd))                as max_usd,
       round(100 * sum(amount_usd) filter (where amount_usd >= p90) / sum(amount_usd)) as pct_revenue_top10pct
from (select *, quantile_cont(amount_usd, 0.9) over (partition by tenant_id) as p90
      from read_parquet('{path}') where status = 'won')
group by tenant_id order by tenant_id
"""


def _decimals_to_float(df):
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


def run(engine):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        df = _decimals_to_float(pd.read_sql(f"select * from marts.{table}", engine))
        df.to_parquet(EXPORT_DIR / f"{table}.parquet", index=False)
        print(f"  {table}.parquet: {len(df)} rows")
    path = (EXPORT_DIR / "fct_deals.parquet").as_posix()
    summary = duckdb.connect().execute(DISTRIBUTION_SQL.format(path=path)).df()
    summary.to_csv(EXPORT_DIR / "deal_size_distribution.csv", index=False)
    print("\n  Won deal size (USD), mean vs median:")
    print(summary.to_string(index=False))
