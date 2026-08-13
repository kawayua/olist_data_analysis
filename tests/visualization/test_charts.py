import pandas as pd
import pytest

from src.visualization.charts import (
    bubble_scatter_chart,
    line_chart,
    ranked_bar_chart,
    retention_heatmap,
)


def test_line_chart_uses_requested_columns():
    frame = pd.DataFrame({"month": ["2024-01"], "revenue": [100.0]})

    figure = line_chart(frame, x="month", y="revenue", title="Revenue")

    assert figure.data[0].x[0] == "2024-01"
    assert figure.data[0].y[0] == 100.0


@pytest.mark.parametrize(
    ("factory", "kwargs"),
    [
        (line_chart, {}),
        (ranked_bar_chart, {"color": None}),
    ],
)
def test_chart_factories_localize_english_revenue_title(factory, kwargs):
    frame = pd.DataFrame({"month": ["2024-01"], "revenue": [100.0]})

    figure = factory(frame, x="month", y="revenue", title="Revenue", **kwargs)

    assert figure.layout.title.text == "收入"


def test_line_chart_uses_chinese_axis_and_hover_labels():
    frame = pd.DataFrame(
        {"month_start": ["2024-01"], "item_revenue": [100.0]}
    )

    figure = line_chart(frame, x="month_start", y="item_revenue", title="收入趋势")

    assert figure.layout.xaxis.title.text == "月份"
    assert figure.layout.yaxis.title.text == "商品金额"
    assert "商品金额" in figure.data[0].hovertemplate


def test_line_chart_keeps_month_value_unformatted_in_hover_template():
    frame = pd.DataFrame(
        {"month_start": ["2024-01"], "item_revenue": [100.0]}
    )

    figure = line_chart(frame, x="month_start", y="item_revenue", title="收入趋势")

    assert "月份=%{x}" in figure.data[0].hovertemplate


def test_ranked_bar_chart_sorts_revenue_and_localizes_category_axis():
    frame = pd.DataFrame(
        {
            "product_category": ["家居", "美妆", "服装"],
            "item_revenue": [200.0, 500.0, 300.0],
        }
    )

    figure = ranked_bar_chart(
        frame,
        x="product_category",
        y="item_revenue",
        title="品类收入排名",
    )

    assert list(figure.data[0].y) == [500.0, 300.0, 200.0]
    assert figure.layout.xaxis.title.text == "商品品类"


def test_retention_heatmap_uses_chinese_cohort_labels():
    matrix = pd.DataFrame(
        [[100.0, 50.0]], index=["2024-01"], columns=[0, 1]
    )

    figure = retention_heatmap(matrix)

    assert figure.layout.xaxis.title.text == "距首购月数"
    assert figure.layout.yaxis.title.text == "首购月份（同期群）"
    assert figure.layout.coloraxis.colorbar.title.text == "留存率（%）"


def test_bubble_scatter_encodes_orders_as_marker_size():
    frame = pd.DataFrame({"item_revenue_mom_pct": [10.0], "item_revenue": [100.0], "order_count": [5]})
    figure = bubble_scatter_chart(frame, "item_revenue_mom_pct", "item_revenue", "order_count", "增长机会矩阵")
    assert figure.data[0].marker.size[0] == 5


def test_bubble_chart_uses_chinese_axis_legend_and_hover_labels():
    frame = pd.DataFrame(
        {
            "average_frequency_orders": [2.0],
            "average_monetary_item_revenue": [100.0],
            "customer_count": [5],
            "customer_segment": ["high_value"],
        }
    )

    figure = bubble_scatter_chart(
        frame,
        "average_frequency_orders",
        "average_monetary_item_revenue",
        "customer_count",
        "客户价值",
        color="customer_segment",
    )

    assert figure.layout.xaxis.title.text == "平均购买次数"
    assert figure.layout.yaxis.title.text == "平均客户商品金额"
    assert figure.layout.legend.title.text == "客户分群"
    assert figure.data[0].name == "高价值客户"
    assert "平均购买次数" in figure.data[0].hovertemplate
    assert "average_frequency_orders" not in figure.data[0].hovertemplate
