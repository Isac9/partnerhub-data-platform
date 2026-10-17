import pandas as pd

from partnerhub.privacy import contains_email, pseudonymize, pseudonymize_email


def test_hash_is_stable_and_case_insensitive():
    a, _ = pseudonymize_email("Awa.Kone@Nova.com", "salt")
    b, _ = pseudonymize_email("  awa.kone@nova.com ", "salt")
    assert a == b


def test_hash_depends_on_the_salt():
    assert pseudonymize_email("a@b.com", "salt1")[0] != pseudonymize_email("a@b.com", "salt2")[0]


def test_domain_is_kept():
    assert pseudonymize_email("awa@nova.io", "s")[1] == "nova.io"


def test_pseudonymize_removes_emails_and_names():
    tables = {
        "acme_companies": pd.DataFrame({"id": ["1"], "contact_email": ["awa@nova.io"], "contact_name": ["Awa Koné"]}),
        "globex_partner_accounts": pd.DataFrame({"Id": ["1"], "Email__c": [None], "Contact_Name__c": ["X"]}),
        "initech_organizations": pd.DataFrame({"id": [1], "email": ["k@x.fr"], "owner_name": ["Kofi"]}),
    }
    out = pseudonymize(tables, "salt")
    acme = out["acme_companies"]
    assert list(acme.columns) == ["id", "contact_email_hash", "contact_email_domain"]
    assert not contains_email(acme.astype(str).to_numpy().ravel())
    assert out["globex_partner_accounts"]["Email__c_hash"].iloc[0] is None  # missing email stays missing


def test_contains_email():
    assert contains_email(["x", "write to awa@nova.io"])
    assert not contains_email(["nova.io", None, 3])
