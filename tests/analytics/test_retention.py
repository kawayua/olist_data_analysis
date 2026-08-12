import pandas as pd

from src.analytics.retention import eligible_for_horizon


def test_customer_without_full_horizon_is_excluded():
    first_purchase = pd.Timestamp("2018-07-01")
    data_end = pd.Timestamp("2018-08-31")

    assert eligible_for_horizon(first_purchase, data_end, days=90) is False


def test_customer_with_exactly_full_horizon_is_eligible():
    first_purchase = pd.Timestamp("2018-06-02")
    data_end = pd.Timestamp("2018-08-31")

    assert eligible_for_horizon(first_purchase, data_end, days=90) is True
