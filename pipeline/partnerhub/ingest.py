"""Extract the three sources and load them, untouched, into the raw schema."""
import json
import time
from decimal import Decimal

import pandas as pd
import requests
from sqlalchemy import text

from .config import ACME_API_URL, DATA_DIR

SOURCES = {
    "acme_companies": "api:/crm/v3/objects/companies",
    "acme_deals": "api:/crm/v3/objects/deals",
    "globex_partner_accounts": "file:globex/partner_accounts.csv",
    "globex_opportunities": "file:globex/opportunities.csv",
    "initech_organizations": "file:initech/organizations.json",
    "initech_deals": "file:initech/deals.json",
}
# tenant -> (deals table, amount column)
DEALS = {"acme": ("acme_deals", "amount"), "globex": ("globex_opportunities", "Amount"), "initech": ("initech_deals", "value")}


def _get(url, params, attempts=15):
    for _ in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code < 500:
                r.raise_for_status()
        except requests.ConnectionError:
            pass
        time.sleep(2)
    raise RuntimeError(f"CRM API unreachable: {url}")


def fetch_all(obj):
    """Follow the cursor pagination until there is no next page."""
    rows, after = [], "0"
    while True:
        body = _get(f"{ACME_API_URL}/crm/v3/objects/{obj}", {"limit": 100, "after": after})
        rows += [{"id": r["id"], **r["properties"]} for r in body["results"]]
        nxt = body.get("paging", {}).get("next")
        if not nxt:
            return rows
        after = nxt["after"]


def _blank_to_none(df):
    df = df.astype(object)
    return df.where(df.notna() & (df != ""), None)


def extract():
    tables = {f"acme_{obj}": pd.DataFrame(fetch_all(obj)) for obj in ("companies", "deals")}
    for name in ("partner_accounts", "opportunities"):
        tables[f"globex_{name}"] = pd.read_csv(DATA_DIR / "globex" / f"{name}.csv", dtype=str, keep_default_na=False)
    for name in ("organizations", "deals"):
        rows = json.loads((DATA_DIR / "initech" / f"{name}.json").read_text(encoding="utf-8"))
        tables[f"initech_{name}"] = pd.DataFrame(rows)
    return {name: _blank_to_none(df) for name, df in tables.items()}


def source_totals(tables):
    """Row count and amount per tenant, computed from the sources (exact decimals)."""
    totals = []
    for tenant, (table, column) in DEALS.items():
        df = tables[table]
        amount = sum((Decimal(str(v)) for v in df[column] if v is not None), Decimal(0))
        totals.append({"tenant_id": tenant, "source_table": table, "row_count": len(df), "amount_total": amount})
    return totals


def load_raw(engine, tables, run_id):
    """Full reload: every column stored as text, plus lineage columns."""
    loaded_at = pd.Timestamp.now(tz="UTC")
    with engine.begin() as conn:
        for name, df in tables.items():
            df = df.astype("string")
            df["_run_id"] = run_id
            df["_loaded_at"] = loaded_at
            df["_source"] = SOURCES[name]
            conn.execute(text(f'drop table if exists raw."{name}" cascade'))
            df.to_sql(name, conn, schema="raw", index=False)


def save_source_totals(engine, totals, run_id):
    rows = [{**t, "run_id": run_id} for t in totals]
    with engine.begin() as conn:
        conn.execute(text("insert into audit.source_totals (run_id, tenant_id, source_table, row_count, amount_total) "
                          "values (:run_id, :tenant_id, :source_table, :row_count, :amount_total)"), rows)
