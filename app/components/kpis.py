"""Consistent KPI display helpers for Streamlit pages."""

from collections.abc import Sequence

import streamlit as st


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


def render_kpis(items: Sequence[tuple[str, float | int | None, str]]) -> None:
    """Render label, formatted value, and optional supporting text for KPIs."""
    columns = st.columns(len(items))
    for column, (label, value, help_text) in zip(columns, items, strict=True):
        column.metric(label, value, help=help_text)
