"""Personal data: pseudonymize at ingestion, then prove nothing leaked."""
import hashlib
import hmac
import re

from sqlalchemy import text

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_SQL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
SCANNED_SCHEMAS = ("raw", "staging", "intermediate", "marts", "analytics")

# table -> (email column, columns dropped because we do not need them: contact names)
PII_RULES = {
    "acme_companies": ("contact_email", ["contact_name"]),
    "globex_partner_accounts": ("Email__c", ["Contact_Name__c"]),
    "initech_organizations": ("email", ["owner_name"]),
}


def pseudonymize_email(email, salt):
    """Keyed hash (HMAC-SHA256): stable, so contacts can still be joined and counted,
    but not reversible without the salt, which never enters the warehouse."""
    normalized = email.strip().lower()
    digest = hmac.new(salt.encode(), normalized.encode(), hashlib.sha256).hexdigest()
    return digest, normalized.rsplit("@", 1)[-1]


def pseudonymize(tables, salt):
    tables = dict(tables)
    for name, (email_col, drop) in PII_RULES.items():
        df = tables[name].copy()
        pairs = [pseudonymize_email(e, salt) if e else (None, None) for e in df[email_col]]
        df[f"{email_col}_hash"] = [p[0] for p in pairs]
        df[f"{email_col}_domain"] = [p[1] for p in pairs]
        tables[name] = df.drop(columns=[email_col, *drop])
    return tables


def contains_email(values):
    return any(isinstance(v, str) and EMAIL_RE.search(v) for v in values)


def scan_for_emails(engine):
    """Look for anything shaped like an email in every text column of the warehouse."""
    leaks = []
    with engine.connect() as conn:
        columns = conn.execute(text(
            "select table_schema, table_name, column_name from information_schema.columns "
            "where table_schema = any(:schemas) and data_type in ('text', 'character varying')"),
            {"schemas": list(SCANNED_SCHEMAS)}).all()
        for schema, table, column in columns:
            n = conn.execute(text(f'select count(*) from "{schema}"."{table}" where "{column}" ~ :pattern'),
                             {"pattern": EMAIL_SQL}).scalar()
            if n:
                leaks.append((f"{schema}.{table}.{column}", n))
    return leaks, len(columns)
