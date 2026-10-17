"""Stop the run when a source sends a value that no mapping knows.

A pipeline that silently drops what it cannot match always looks clean.
Here an unknown stage, partner type or country is an error, not noise.
"""
import pandas as pd

from .config import SEEDS_DIR

# mapping kind -> (seed file, is the mapping specific to each tenant?)
MAPPINGS = {
    "stage": ("stage_mapping.csv", True),
    "partner_type": ("partner_type_mapping.csv", True),
    "country": ("country_mapping.csv", False),
}
# (tenant, raw table, column, mapping kind)
FIELDS = [
    ("acme", "acme_deals", "dealstage", "stage"),
    ("acme", "acme_companies", "partner_type", "partner_type"),
    ("acme", "acme_companies", "country", "country"),
    ("globex", "globex_opportunities", "StageName", "stage"),
    ("globex", "globex_partner_accounts", "Type", "partner_type"),
    ("globex", "globex_partner_accounts", "BillingCountry", "country"),
    ("initech", "initech_deals", "stage_key", "stage"),
    ("initech", "initech_organizations", "label", "partner_type"),
    ("initech", "initech_organizations", "address_country", "country"),
]


def initech_stage_key(status, stage_id):
    """Pipedrive keeps status (won/lost/open) and pipeline step apart; open deals are mapped per step."""
    return f"open:{int(stage_id)}" if status == "open" else status


def known_values(kind):
    file, per_tenant = MAPPINGS[kind]
    df = pd.read_csv(SEEDS_DIR / file, dtype=str, keep_default_na=False)
    return {(row.tenant_id if per_tenant else "*", row.source_value) for row in df.itertuples()}


def find_unmapped(tables, known=None):
    known = known or {kind: known_values(kind) for kind in MAPPINGS}
    issues = []
    for tenant, table, column, kind in FIELDS:
        df = tables[table]
        if column == "stage_key":
            values = pd.Series([initech_stage_key(s, i) for s, i in zip(df["status"], df["stage_id"])], dtype=object)
        else:
            values = df[column]
        scope = tenant if MAPPINGS[kind][1] else "*"
        for value, n in values.value_counts(dropna=False).items():
            value = None if pd.isna(value) else value
            if (scope, value) not in known[kind]:
                issues.append({"tenant_id": tenant, "field": f"{table}.{column}", "source_value": value, "row_count": int(n)})
    return issues
