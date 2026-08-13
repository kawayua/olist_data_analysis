"""Pure Plotly chart factories used by Streamlit pages."""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from app.components.presentation import display_label, display_value

CHINESE_TITLES = {
    "Revenue": "收入",
}

CURRENCY_COLUMNS = {
    "item_revenue",
    "payment_value",
    "item_revenue_aov",
    "new_customer_item_revenue",
    "returning_customer_item_revenue",
    "freight_revenue",
    "average_monetary_item_revenue",
    "first_purchase_item_revenue",
    "repeat_customer_item_revenue",
}


def localized_chart_frame(
    frame: pd.DataFrame, *categorical_columns: str | None
) -> pd.DataFrame:
    """Return a chart-only copy with localized categorical values."""
    columns = [
        column
        for column in categorical_columns
        if column is not None and column in frame.columns
    ]
    if not columns:
        return frame
    localized = frame.copy(deep=True)
    for column in columns:
        localized[column] = localized[column].map(
            lambda value, display_column=column: display_value(
                display_column, value
            )
        )
    return localized


def hover_value_template(column: str, coordinate: str) -> str:
    """Format a Plotly coordinate using the business unit of a metric."""
    if column in CURRENCY_COLUMNS:
        return f"R$%{{{coordinate}:,.2f}}"
    if column.endswith("_pct"):
        return f"%{{{coordinate}:.3f}}%"
    if column == "average_review_score":
        return f"%{{{coordinate}:.3f}}分"
    if column.endswith("_days"):
        return f"%{{{coordinate}:.3f}}天"
    return f"%{{{coordinate}}}"


def localized_chart_title(title: str) -> str:
    """Return a Chinese title so chart factories never expose English text."""
    if title in CHINESE_TITLES:
        return CHINESE_TITLES[title]
    if any("a" <= character.lower() <= "z" for character in title):
        return "数据分析"
    return title


def apply_chart_layout(figure: Figure, x: str, y: str) -> Figure:
    """Apply the dashboard's shared labels, hover format, and visual style."""
    x_label = display_label(x)
    y_label = display_label(y)
    figure.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": "#13233D"},
        legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1.02},
    )
    figure.update_xaxes(title=x_label, gridcolor="#E5E7EB")
    figure.update_yaxes(title=y_label, gridcolor="#E5E7EB")
    figure.update_traces(
        hovertemplate=(
            f"{x_label}={hover_value_template(x, 'x')}<br>"
            f"{y_label}={hover_value_template(y, 'y')}<extra></extra>"
        )
    )
    return figure


def line_chart(frame: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    """Return a line chart using the requested DataFrame columns."""
    figure = px.line(
        frame,
        x=x,
        y=y,
        title=localized_chart_title(title),
        labels={name: display_label(name) for name in frame.columns},
    )
    return apply_chart_layout(figure, x, y)


def ranked_bar_chart(
    frame: pd.DataFrame, x: str, y: str, title: str, color: str | None = None
) -> Figure:
    """Return a descending ranked bar chart with dashboard styling."""
    chart_frame = localized_chart_frame(frame, x, color)
    ordered = chart_frame.sort_values(y, ascending=False)
    figure = px.bar(
        ordered,
        x=x,
        y=y,
        color=color,
        text=y,
        labels={name: display_label(name) for name in ordered.columns},
        title=localized_chart_title(title),
    )
    return apply_chart_layout(figure, x, y)


def retention_heatmap(matrix: pd.DataFrame) -> Figure:
    """Return a Chinese-labelled cohort retention heatmap."""
    figure = px.imshow(
        matrix,
        labels={
            "x": "距首购月数",
            "y": "首购月份（同期群）",
            "color": "留存率（%）",
        },
        color_continuous_scale="Blues",
        aspect="auto",
    )
    figure.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": "#13233D"},
    )
    figure.update_xaxes(gridcolor="#E5E7EB")
    figure.update_yaxes(gridcolor="#E5E7EB")
    figure.update_traces(hovertemplate="留存率（%）=%{z:.1f}%<extra></extra>")
    return figure


def bubble_scatter_chart(
    frame: pd.DataFrame,
    x: str,
    y: str,
    size: str,
    title: str,
    color: str | None = None,
) -> Figure:
    """Return a scatter plot whose marker area encodes the requested measure."""
    chart_frame = localized_chart_frame(frame, color)
    figure = px.scatter(
        chart_frame,
        x=x,
        y=y,
        size=size,
        color=color,
        title=localized_chart_title(title),
        labels={name: display_label(name) for name in chart_frame.columns},
    )
    return apply_chart_layout(figure, x, y)
