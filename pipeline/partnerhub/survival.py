"""How long does a deal take to close? A survival question, because open deals are censored.

Taking the median of closed deals only ignores the slow deals that are still open,
so it is biased low. Kaplan-Meier uses the open deals too.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from lifelines import KaplanMeierFitter
from sqlalchemy import text

from .config import EXPORT_DIR, IMAGES_DIR


def run(engine):
    deals = pd.read_parquet(EXPORT_DIR / "fct_deals.parquet")
    partners = pd.read_parquet(EXPORT_DIR / "dim_partners.parquet")
    df = deals.merge(partners[["partner_id", "partner_type"]], on="partner_id")
    rows = []
    fig, ax = plt.subplots(figsize=(8, 5))
    for ptype, g in df.groupby("partner_type"):
        closed = ~g["is_censored"].astype(bool)
        kmf = KaplanMeierFitter().fit(g["duration_days"].astype(float), event_observed=closed, label=ptype)
        kmf.plot_survival_function(ax=ax)
        rows.append({
            "partner_type": ptype,
            "deals": len(g),
            "still_open": int((~closed).sum()),
            "median_days_closed_only": round(float(g.loc[closed, "duration_days"].median()), 1),
            "median_days_kaplan_meier": round(float(kmf.median_survival_time_), 1),
        })
    ax.set_xlabel("Days since the deal was created")
    ax.set_ylabel("Share of deals still open")
    ax.set_title("Time to close by partner type (Kaplan-Meier, open deals censored)")
    ax.set_xlim(0, 400)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(IMAGES_DIR / "time_to_close.png", dpi=120)
    plt.close(fig)

    result = pd.DataFrame(rows)
    with engine.begin() as conn:
        conn.execute(text("create schema if not exists analytics"))
        result.to_sql("time_to_close", conn, schema="analytics", if_exists="replace", index=False)
    print(result.to_string(index=False))
