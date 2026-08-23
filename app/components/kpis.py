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


def render_kpis(items: Sequence[tuple[str, str, str]]) -> None:
    """Render responsive, native metric cards with concise business context."""
    with st.container(horizontal=True, gap="small"):
        for label, value, help_text in items:
            with st.container(gap="small"):
                st.metric(label, value, border=True)
                st.caption(help_text)
