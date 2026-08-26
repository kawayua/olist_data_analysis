import pandas as pd

from src.analytics.repository import AnalyticsFilters, AnalyticsRepository


def test_monthly_growth_binds_date_filters_and_excludes_incomplete_months(
    monkeypatch,
):
    captured = {}

    def fake_read_sql(query, engine, params):
        captured["sql"] = str(query)
        captured["params"] = params
        return pd.DataFrame({"month_start": []})

    monkeypatch.setattr("src.analytics.repository.pd.read_sql", fake_read_sql)
    repository = AnalyticsRepository(engine=object())

    result = repository.monthly_growth(
        AnalyticsFilters(start_month="2017-01-01", end_month="2017-12-01")
    )

    assert result.empty
    assert "marts.monthly_growth" in captured["sql"]
    assert "is_complete_month" in captured["sql"]
    assert captured["params"] == {
        "start_month": "2017-01-01",
        "end_month": "2017-12-01",
    }


def test_repository_exposes_each_governed_mart_query(monkeypatch):
    queries = []

    def fake_read_sql(query, engine, params):
        queries.append((str(query), params))
        return pd.DataFrame()

    monkeypatch.setattr("src.analytics.repository.pd.read_sql", fake_read_sql)
    repository = AnalyticsRepository(engine=object())

    repository.cohort_retention(AnalyticsFilters())
    repository.customer_segments(AnalyticsFilters())
    repository.product_performance(
        AnalyticsFilters(product_category="health_beauty")
    )
    repository.delivery_experience(AnalyticsFilters())

    assert "marts.cohort_retention" in queries[0][0]
    assert "marts.customer_segment_strategy" in queries[1][0]
    assert "marts.product_performance" in queries[2][0]
    assert queries[2][1] == {"product_category": "health_beauty"}
    assert "marts.delivery_experience" in queries[3][0]


def test_state_repository_uses_a_bound_customer_state_parameter(monkeypatch):
    queries = []

    def fake_read_sql(query, engine, params):
        queries.append((str(query), params))
        return pd.DataFrame({"customer_state": ["SP"]})

    monkeypatch.setattr("src.analytics.repository.pd.read_sql", fake_read_sql)
    repository = AnalyticsRepository(engine=object())

    states = repository.available_customer_states()
    performance = repository.state_performance(AnalyticsFilters(customer_state="SP"))

    assert states["customer_state"].tolist() == ["SP"]
    assert performance["customer_state"].tolist() == ["SP"]
    assert "marts.state_performance" in queries[0][0]
    assert "marts.state_performance" in queries[1][0]
    assert "SP" not in queries[1][0]
    assert queries[1][1] == {"customer_state": "SP"}


def test_repository_exposes_customer_value_and_repurchase_marts(monkeypatch):
    queries = []

    def fake_read_sql(query, engine, params):
        queries.append(str(query))
        return pd.DataFrame()

    monkeypatch.setattr("src.analytics.repository.pd.read_sql", fake_read_sql)
    repository = AnalyticsRepository(engine=object())

    repository.customer_value_analysis()
    repository.repurchase_behavior()
    repository.repurchase_intervals()
    repository.delivery_rating_analysis()

    assert "marts.customer_value_analysis" in queries[0]
    assert "marts.repurchase_behavior" in queries[1]
    assert "marts.repurchase_intervals" in queries[2]
    assert "marts.delivery_rating_analysis" in queries[3]


def test_repository_reads_only_time_safe_features_for_model_scoring(monkeypatch):
    """Selecting labels or future fields would leak outcomes into live scoring."""
    captured = {}

    def fake_read_sql(query, engine, params):
        captured["sql"] = str(query)
        captured["params"] = params
        return pd.DataFrame({"customer_key": [42]})

    monkeypatch.setattr("src.analytics.repository.pd.read_sql", fake_read_sql)
    repository = AnalyticsRepository(engine=object())

    frame = repository.ml_customer_features_for_scoring()

    assert frame["customer_key"].tolist() == [42]
    assert "marts.ml_customer_features" in captured["sql"]
    assert "first_order_item_revenue" in captured["sql"]
    assert "first_order_primary_category" in captured["sql"]
    assert "first_order_delivery_vs_estimate_days" in captured["sql"]
    assert "SELECT *" not in captured["sql"].upper()
    assert "repurchased_within_90d" not in captured["sql"]
    assert "future_" not in captured["sql"]
    assert captured["params"] == {}
