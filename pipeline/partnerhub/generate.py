"""Generate fake partner data for three tenants, each exporting from a different CRM.

Every tenant names the same things differently (deal stages, partner types,
countries, dates, currencies). Making them line up is the whole point of the project.

    python -m partnerhub.generate                    # clean data
    python -m partnerhub.generate --inject-anomaly   # globex starts writing "Closed-Won"
"""
import argparse
import csv
import json
import math
import random
import unicodedata
from datetime import datetime, timedelta

from .config import AS_OF, DATA_DIR

START = datetime(2024, 1, 1)
FIRST = ["Awa", "Kofi", "Marie", "John", "Fatou", "Ibrahim", "Sarah", "Paul", "Aminata", "David", "Chloé", "Moussa"]
LAST = ["Koné", "Diallo", "Smith", "Martin", "Traoré", "Johnson", "Bamba", "Dubois", "Ndiaye", "Brown"]
WORD_A = ["Nova", "Blue", "Prime", "Delta", "Apex", "Sahel", "Atlantic", "Vertex", "Lagoon", "Summit"]
WORD_B = ["Systems", "Solutions", "Partners", "Digital", "Consulting", "Networks", "Labs", "Group"]

# canonical partner type -> (median days to close, win rate)
TYPE_PROFILE = {"reseller": (40, 0.45), "referral": (75, 0.30), "technology": (110, 0.38)}
TYPE_WEIGHTS = {"reseller": 5, "referral": 3, "technology": 2}
COUNTRY_WEIGHTS = {"CI": 4, "SN": 2, "US": 3, "FR": 2}

TENANTS = {
    "acme": {  # HubSpot-like, served by the CRM API
        "n_partners": 120, "n_deals": 1500, "currency": "USD", "units_per_usd": 1.0, "decimals": 2,
        "types": {"reseller": "Reseller", "referral": "Referral Partner", "technology": "Tech Partner"},
        "countries": {"CI": "Ivory Coast", "SN": "Senegal", "US": "United States", "FR": "France"},
        "stages": {"won": ["closedwon"], "lost": ["closedlost"],
                   "open": ["appointmentscheduled", "qualifiedtobuy", "presentationscheduled", "contractsent"]},
    },
    "globex": {  # Salesforce-like CSV exports
        "n_partners": 80, "n_deals": 1000, "currency": "EUR", "units_per_usd": 0.92, "decimals": 2,
        "types": {"reseller": "VAR", "referral": "Referral", "technology": "Technology"},
        "countries": {"CI": "Côte d'Ivoire", "SN": "Sénégal", "US": "USA", "FR": "France"},
        "stages": {"won": ["Closed Won"], "lost": ["Closed Lost"],
                   "open": ["Prospecting", "Qualification", "Proposal/Price Quote", "Negotiation/Review"]},
    },
    "initech": {  # Pipedrive-like JSON exports
        "n_partners": 60, "n_deals": 700, "currency": "XOF", "units_per_usd": 605.0, "decimals": 0,
        "types": {"reseller": "reseller", "referral": "affiliate", "technology": "integration"},
        "countries": {"CI": "CIV", "SN": "SEN", "US": "USA", "FR": "FRA"},
        "stages": {"won": ["won"], "lost": ["lost"], "open": ["open:1", "open:2", "open:3", "open:4"]},
    },
}


def ascii_lower(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def make_partners(rng, cfg):
    partners = []
    for i in range(1, cfg["n_partners"] + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        company = f"{rng.choice(WORD_A)} {rng.choice(WORD_B)}"
        domain = ascii_lower(company).replace(" ", "") + rng.choice([".com", ".io", ".africa", ".fr"])
        partners.append({
            "n": i,
            "type": rng.choices(list(TYPE_WEIGHTS), weights=list(TYPE_WEIGHTS.values()))[0],
            "country": rng.choices(list(COUNTRY_WEIGHTS), weights=list(COUNTRY_WEIGHTS.values()))[0],
            "company": company,
            "contact": f"{first} {last}",
            "email": f"{ascii_lower(first)}.{ascii_lower(last)}@{domain}",
            "created": START + timedelta(days=rng.randint(0, 200), hours=rng.randint(8, 18)),
        })
    return partners


def make_deals(rng, cfg, partners):
    span = (AS_OF - START).days
    deals = []
    for j in range(1, cfg["n_deals"] + 1):
        p = rng.choice(partners)
        created = (START + timedelta(days=rng.uniform(0, span))).replace(microsecond=0)
        median, win_rate = TYPE_PROFILE[p["type"]]
        closed = (created + timedelta(days=rng.lognormvariate(math.log(median), 0.7))).replace(microsecond=0)
        expected = closed
        if closed > AS_OF:
            status, closed = "open", None
            expected = AS_OF + timedelta(days=rng.randint(7, 90))
        else:
            status = "won" if rng.random() < win_rate else "lost"
        amount = rng.lognormvariate(math.log(8000), 1.0) * cfg["units_per_usd"]
        deals.append({"n": j, "partner": p["n"], "status": status, "label": rng.choice(cfg["stages"][status]),
                      "created": created, "closed": closed, "expected": expected,
                      "amount": round(amount, cfg["decimals"])})
    return deals


def write_acme(cfg, partners, deals, out, inject):
    iso = "%Y-%m-%dT%H:%M:%S.000Z"
    companies = [{"id": str(p["n"]), "name": p["company"], "contact_email": p["email"], "contact_name": p["contact"],
                  "partner_type": cfg["types"][p["type"]], "country": cfg["countries"][p["country"]],
                  "createdate": p["created"].strftime(iso)} for p in partners]
    rows = [{"id": str(50000 + d["n"]), "partner_company_id": str(d["partner"]), "amount": f"{d['amount']:.2f}",
             "deal_currency_code": cfg["currency"], "dealstage": d["label"], "createdate": d["created"].strftime(iso),
             "closedate": d["closed"].strftime(iso) if d["closed"] else None} for d in deals]
    (out / "companies.json").write_text(json.dumps(companies, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "deals.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def write_globex(cfg, partners, deals, out, inject):
    accounts = [{"Id": f"001{p['n']:06d}", "Name": p["company"], "Email__c": p["email"], "Contact_Name__c": p["contact"],
                 "Type": cfg["types"][p["type"]], "BillingCountry": cfg["countries"][p["country"]]} for p in partners]
    opps = []
    for d in deals:
        stage = d["label"]
        if inject and stage == "Closed Won" and d["n"] % 7 == 0:
            stage = "Closed-Won"  # a new spelling appears in the source
        # Salesforce always fills CloseDate: the real date for closed deals, the *expected* one for open deals.
        opps.append({"Id": f"006{d['n']:06d}", "Partner_Account__c": f"001{d['partner']:06d}",
                     "Amount": f"{d['amount']:.2f}", "CurrencyIsoCode": cfg["currency"], "StageName": stage,
                     "CreatedDate": d["created"].strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
                     "CloseDate": d["expected"].strftime("%Y-%m-%d")})
    for name, rows in (("partner_accounts", accounts), ("opportunities", opps)):
        with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def write_initech(cfg, partners, deals, out, inject):
    fmt = "%Y-%m-%d %H:%M:%S"
    orgs = [{"id": 100 + p["n"], "name": p["company"], "email": p["email"], "owner_name": p["contact"],
             "label": cfg["types"][p["type"]], "address_country": cfg["countries"][p["country"]],
             "add_time": p["created"].strftime(fmt)} for p in partners]
    rows = []
    for d in deals:
        status, _, stage = d["label"].partition(":")
        rows.append({"id": 9000 + d["n"], "org_id": 100 + d["partner"], "value": d["amount"], "currency": cfg["currency"],
                     "status": status, "stage_id": int(stage) if stage else 4, "add_time": d["created"].strftime(fmt),
                     "close_time": d["closed"].strftime(fmt) if d["closed"] else None})
    (out / "organizations.json").write_text(json.dumps(orgs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "deals.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


WRITERS = {"acme": write_acme, "globex": write_globex, "initech": write_initech}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inject-anomaly", action="store_true")
    args = parser.parse_args(argv)
    for i, (tenant, cfg) in enumerate(TENANTS.items()):
        rng = random.Random(42 + i)
        partners = make_partners(rng, cfg)
        deals = make_deals(rng, cfg, partners)
        out = DATA_DIR / tenant
        out.mkdir(parents=True, exist_ok=True)
        WRITERS[tenant](cfg, partners, deals, out, args.inject_anomaly)
        print(f"  {tenant}: {len(partners)} partners, {len(deals)} deals -> {out}")


if __name__ == "__main__":
    main()
