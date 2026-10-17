import random

from partnerhub.config import AS_OF
from partnerhub.generate import TENANTS, make_deals, make_partners


def deals(tenant="globex"):
    rng = random.Random(1)
    cfg = TENANTS[tenant]
    return make_deals(rng, cfg, make_partners(rng, cfg))


def test_open_deals_have_no_close_date_but_an_expected_one():
    for d in deals():
        if d["status"] == "open":
            assert d["closed"] is None and d["expected"] > AS_OF
        else:
            assert d["created"] <= d["closed"] <= AS_OF


def test_labels_belong_to_the_tenant_vocabulary():
    vocab = TENANTS["acme"]["stages"]
    assert all(d["label"] in vocab[d["status"]] for d in deals("acme"))
