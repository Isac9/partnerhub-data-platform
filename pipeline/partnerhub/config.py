import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
EXPORT_DIR = DATA_DIR / "exports"
DBT_DIR = ROOT / "dbt"
SEEDS_DIR = DBT_DIR / "seeds"
IMAGES_DIR = ROOT / "docs" / "images"

# Reporting date: deals still open on this day are "censored" in the survival analysis.
AS_OF = datetime(2026, 9, 30)

ACME_API_URL = os.environ.get("ACME_API_URL", "http://localhost:8010")
PII_SALT = os.environ.get("PII_SALT", "dev-only-salt-change-me")


def db_url():
    env = os.environ.get
    return (f"postgresql+psycopg2://{env('POSTGRES_USER', 'partnerhub')}:{env('POSTGRES_PASSWORD', 'partnerhub')}"
            f"@{env('POSTGRES_HOST', 'localhost')}:{env('POSTGRES_PORT', '5432')}/{env('POSTGRES_DB', 'partnerhub')}")
