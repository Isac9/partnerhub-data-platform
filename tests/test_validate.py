import pandas as pd
import pytest

from partnerhub.validate import find_unmapped, initech_stage_key, known_values


def tables(stage="Closed Won", country="France"):
    return {
        "acme_deals": pd.DataFrame({"dealstage": ["closedwon"]}),
        "acme_companies": pd.DataFrame({"partner_type": ["Reseller"], "country": ["Senegal"]}),
        "globex_opportunities": pd.DataFrame({"StageName": ["Closed Won", stage]}),
        "globex_partner_accounts": pd.DataFrame({"Type": ["VAR"], "BillingCountry": [country]}),
        "initech_deals": pd.DataFrame({"status": ["open", "won"], "stage_id": [2, 4]}),
        "initech_organizations": pd.DataFrame({"label": ["affiliate"], "address_country": ["CIV"]}),
    }


def test_clean_sources_have_no_issue():
    assert find_unmapped(tables()) == []


def test_new_spelling_is_caught():
    issues = find_unmapped(tables(stage="Closed-Won"))
    assert issues == [{"tenant_id": "globex", "field": "globex_opportunities.StageName",
                       "source_value": "Closed-Won", "row_count": 1}]


def test_missing_value_is_caught():
    issues = find_unmapped(tables(country=None))
    assert issues[0]["source_value"] is None


def test_stage_mappings_are_per_tenant():
    # "won" is valid for initech but means nothing for globex.
    assert ("initech", "won") in known_values("stage")
    assert ("globex", "won") not in known_values("stage")


@pytest.mark.parametrize("status,stage_id,expected", [("open", 3, "open:3"), ("won", 4, "won"), ("lost", 1, "lost")])
def test_initech_stage_key(status, stage_id, expected):
    assert initech_stage_key(status, stage_id) == expected
