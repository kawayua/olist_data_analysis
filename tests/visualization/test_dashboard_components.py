import pandas as pd

from app.components.filters import DashboardFilters
from app.components.kpis import format_kpi_value, render_kpis
from app.components.presentation import display_dataframe, display_label


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


def test_display_label_keeps_unknown_column_name():
    assert display_label("unmapped_metric") == "unmapped_metric"
