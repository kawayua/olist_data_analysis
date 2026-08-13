import pandas as pd
import pytest

from app.components.filters import DashboardFilters
from app.components.kpis import format_kpi_value, render_kpis
from app.components.presentation import (
    display_dataframe,
    display_label,
    summarize_state_performance,
)


def test_dashboard_filters_convert_to_repository_filters():
    filters = DashboardFilters(
        start_month="2017-01-01",
        end_month="2017-12-01",
        customer_state="SP",
        product_category="health_beauty",
        include_incomplete_months=False,
    )

    repository_filters = filters.to_repository_filters()

    assert repository_filters.start_month == "2017-01-01"
    assert repository_filters.end_month == "2017-12-01"
    assert repository_filters.customer_state == "SP"
    assert repository_filters.product_category == "health_beauty"
    assert repository_filters.include_incomplete_months is False


def test_format_kpi_value_handles_numbers_and_missing_values():
    assert format_kpi_value(1234.5, prefix="R$", decimals=1) == "R$1,234.5"
    assert format_kpi_value(None) == "—"


def test_render_kpis_accepts_preformatted_page_values():
    render_kpis([("商品金额", "R$1,234", "已送达订单")])


def test_display_dataframe_renames_without_mutating_source():
    source = pd.DataFrame({"item_revenue": [123.0], "customer_state": ["SP"]})

    displayed = display_dataframe(source)

    assert list(displayed.columns) == ["商品金额", "客户所在州"]
    assert list(source.columns) == ["item_revenue", "customer_state"]


def test_display_dataframe_localizes_state_and_delivery_metrics_without_mutation():
    source = pd.DataFrame(
        {
            "payment_value": [120.0],
            "item_revenue_aov": [100.0],
            "delayed_delivery_rate_pct": [12.5],
            "first_purchase_customer_count": [8],
            "eligible_first_purchase_customer_count": [7],
            "eligible_first_purchase_customers": [7],
            "repurchased_first_purchase_customers": [3],
            "repurchase_rate_90d_pct": [42.857],
            "average_delivery_days": [9.2],
            "median_delivery_days": [8.7],
            "average_delivery_vs_estimate_days": [-1.1],
        }
    )

    displayed = display_dataframe(source)

    assert list(displayed.columns) == [
        "支付金额",
        "商品金额客单价",
        "延迟送达率（%）",
        "首购客户数",
        "符合条件的首购客户数",
        "符合条件的首购客户数",
        "已复购首购客户数",
        "90天复购率（%）",
        "平均配送天数",
        "配送天数中位数",
        "相对预计送达天数",
    ]
    assert list(source.columns) == [
        "payment_value",
        "item_revenue_aov",
        "delayed_delivery_rate_pct",
        "first_purchase_customer_count",
        "eligible_first_purchase_customer_count",
        "eligible_first_purchase_customers",
        "repurchased_first_purchase_customers",
        "repurchase_rate_90d_pct",
        "average_delivery_days",
        "median_delivery_days",
        "average_delivery_vs_estimate_days",
    ]


def test_display_dataframe_translates_columns_and_segment_values():
    source = pd.DataFrame(
        {
            "customer_segment": ["high_value"],
            "customer_share_pct": [12.5],
            "repeat_customer_item_revenue": [100.0],
        }
    )

    displayed = display_dataframe(source)

    assert list(displayed.columns) == [
        "客户分群",
        "客户占比（%）",
        "复购客户商品金额",
    ]
    assert displayed.iloc[0, 0] == "高价值客户"
    assert list(source.columns) == [
        "customer_segment",
        "customer_share_pct",
        "repeat_customer_item_revenue",
    ]


def test_display_dataframe_translates_product_category_values():
    displayed = display_dataframe(
        pd.DataFrame({"product_category": ["health_beauty"]})
    )

    assert displayed.iloc[0, 0] == "美妆与健康"


def test_display_label_keeps_unknown_column_name():
    assert display_label("unmapped_metric") == "unmapped_metric"


def test_state_summary_weights_rates_by_their_denominators():
    frame = pd.DataFrame(
        {
            "order_count": [100, 1],
            "customer_count": [90, 1],
            "item_revenue": [1_000.0, 50.0],
            "delayed_delivery_rate_pct": [10.0, 100.0],
            "eligible_first_purchase_customers": [100, 1],
            "repurchased_first_purchase_customers": [20, 1],
        }
    )

    summary = summarize_state_performance(frame)

    assert summary.delayed_delivery_rate_pct == pytest.approx(10.891, abs=0.001)
    assert summary.repurchase_rate_90d_pct == pytest.approx(20.792, abs=0.001)
