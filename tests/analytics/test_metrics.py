import pandas as pd

from src.analytics.metrics import get_metric_definition, summarize_monthly_growth


def test_repeat_rate_definition_contains_denominator_rule():
    metric = get_metric_definition("repeat_rate_90d")

    assert metric.unit == "percent"
    assert "完整90天观察期" in metric.denominator


def test_monthly_growth_counts_new_and_returning_customers_and_order_aov():
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "customer_key": [1, 1, 2, 3],
            "purchased_at": pd.to_datetime(
                ["2018-01-03", "2018-02-05", "2018-02-06", "2018-01-20"]
            ),
            "item_revenue": [100.0, 80.0, 50.0, 20.0],
            "payment_value": [110.0, 90.0, 55.0, 25.0],
        }
    )

    result = summarize_monthly_growth(orders)
    february = result.loc[result["month"] == pd.Timestamp("2018-02-01")].iloc[0]

    assert february["new_customers"] == 1
    assert february["returning_customers"] == 1
    assert february["orders"] == 2
    assert february["item_revenue"] == 130.0
    assert february["item_revenue_aov"] == 65.0
