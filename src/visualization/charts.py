"""Pure Plotly chart factories used by Streamlit pages."""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from app.components.presentation import display_label


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
            f"{x_label}=%{{x}}<br>{y_label}=R$%{{y:,.0f}}<extra></extra>"
        )
    )
    return figure


def line_chart(frame: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    """Return a line chart using the requested DataFrame columns."""
    figure = px.line(
        frame,
        x=x,
        y=y,
        title=title,
        labels={name: display_label(name) for name in frame.columns},
    )
    return apply_chart_layout(figure, x, y)


def ranked_bar_chart(
    frame: pd.DataFrame, x: str, y: str, title: str, color: str | None = None
) -> Figure:
    """Return a descending ranked bar chart with dashboard styling."""
    ordered = frame.sort_values(y, ascending=False)
    figure = px.bar(
        ordered,
        x=x,
        y=y,
        color=color,
        text=y,
        labels={name: display_label(name) for name in ordered.columns},
        title=title,
    )
    return apply_chart_layout(figure, x, y)


def retention_heatmap(matrix: pd.DataFrame) -> Figure:
    """Return a Chinese-labelled cohort retention heatmap."""
    figure = px.imshow(
        matrix,
        labels={
            "x": "距首购月数",
            "y": "Cohort 首购月份",
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
    figure.update_traces(hovertemplate="留存率（%）=%{z:.1f}<extra></extra>")
    return figure
