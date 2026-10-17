"""Run the whole pipeline, from the three CRMs to the analysis datasets.

    python -m partnerhub.run_all
"""
import subprocess
import sys

import pandas as pd
from sqlalchemy import create_engine, text

from . import export, generate, ingest, privacy, survival, validate
from .config import DATA_DIR, DBT_DIR, PII_SALT, db_url


class PipelineError(Exception):
    pass


def step(title):
    print(f"\n=== {title} ===", flush=True)


def dbt(*args):
    subprocess.run(["dbt", *args, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)], check=True)


def finish(engine, run_id, status, message=None):
    with engine.begin() as conn:
        conn.execute(text("update audit.pipeline_runs set finished_at = now(), status = :s, message = :m where run_id = :r"),
                     {"s": status, "m": message, "r": run_id})


def main():
    engine = create_engine(db_url())
    if not (DATA_DIR / "globex" / "opportunities.csv").exists():
        step("0. Generating the source data")
        generate.main([])

    with engine.begin() as conn:
        run_id = conn.execute(text("insert into audit.pipeline_runs default values returning run_id")).scalar()
    print(f"Run #{run_id}")

    try:
        step("1. Extracting from the 3 CRMs")
        tables = ingest.extract()
        for name, df in tables.items():
            print(f"  {name}: {len(df)} rows")

        step("2. Pseudonymizing personal data")
        tables = privacy.pseudonymize(tables, PII_SALT)
        print("  emails -> HMAC-SHA256 + domain, contact names dropped")

        step("3. Checking for values no mapping knows")
        issues = validate.find_unmapped(tables)
        if issues:
            pd.DataFrame([{**i, "run_id": run_id} for i in issues]).to_sql(
                "unmapped_values", engine, schema="audit", if_exists="append", index=False)
            print(pd.DataFrame(issues).to_string(index=False))
            raise PipelineError(f"{len(issues)} unknown value(s): add them to dbt/seeds/*_mapping.csv, then re-run")
        print("  every stage, partner type and country is mapped")

        step("4. Loading raw tables and source totals")
        ingest.load_raw(engine, tables, run_id)
        totals = ingest.source_totals(tables)
        ingest.save_source_totals(engine, totals, run_id)
        for t in totals:
            print(f"  {t['tenant_id']}: {t['row_count']} deals, {t['amount_total']} in source currency")

        step("5. dbt: seeds, models, tests (reconciliation included)")
        dbt("seed", "--full-refresh")
        dbt("run")
        dbt("test")

        step("6. Privacy scan: no email may remain in the warehouse")
        leaks, scanned = privacy.scan_for_emails(engine)
        if leaks:
            raise PipelineError(f"emails found in: {leaks}")
        print(f"  {scanned} text columns scanned, 0 email found")

        step("7. Analysis datasets (Parquet + DuckDB)")
        export.run(engine)

        step("8. Survival analysis: time to close")
        survival.run(engine)

        step("9. Documentation and lineage (dbt docs)")
        dbt("docs", "generate")
    except (PipelineError, subprocess.CalledProcessError) as exc:
        finish(engine, run_id, "failed", str(exc))
        print(f"\nPIPELINE FAILED: {exc}")
        sys.exit(1)

    finish(engine, run_id, "success")
    print("\nPIPELINE OK. Docs: http://localhost:8082")


if __name__ == "__main__":
    main()
