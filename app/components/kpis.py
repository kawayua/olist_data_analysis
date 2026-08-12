"""Consistent KPI display helpers for Streamlit pages."""

from collections.abc import Sequence

import streamlit as st

from app.components.layout import render_kpi_card


def format_kpi_value(
    value: float | None,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 0,
) -> str:
    """Format a numeric KPI while showing missing values explicitly."""
    if value is None:
        return "—"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def render_kpis(items: Sequence[tuple[str, str, str]]) -> None:
    """Render label, preformatted value, and supporting text for KPIs."""
    columns = st.columns(len(items))
    for column, (label, value, help_text) in zip(columns, items, strict=True):
        with column:
            render_kpi_card(label, value, help_text)
