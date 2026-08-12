"""Shared visual layout primitives for Streamlit dashboard pages."""

from html import escape

import streamlit as st


def apply_dashboard_theme() -> None:
    """Inject the dashboard's shared background, cards, and responsive spacing."""
    st.markdown(
        """
        <style>
        .stApp { background: #f6f8fb; }
        [data-testid="stSidebar"] { background: #ffffff; }
        [data-testid="stSidebar"] h2 { color: #172b4d; font-size: 1.1rem; }
        .dashboard-card {
            background: #ffffff; border: 1px solid #e5eaf1; border-radius: 12px;
            box-shadow: 0 4px 14px rgba(20, 42, 74, 0.06); padding: 1rem 1.1rem;
            height: 100%;
        }
        .dashboard-kpi-label { color: #5b6b82; font-size: 0.85rem; margin-bottom: 0.3rem; }
        .dashboard-kpi-value { color: #172b4d; font-size: 1.65rem; font-weight: 700; }
        .dashboard-kpi-help { color: #758399; font-size: 0.8rem; margin-top: 0.35rem; }
        .dashboard-scope { color: #5b6b82; font-size: 0.9rem; }
        @media (max-width: 700px) {
            .dashboard-card { margin-bottom: 0.75rem; }
            .dashboard-kpi-value { font-size: 1.4rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, description: str, scope: str) -> None:
    """Render a consistently labelled dashboard page header."""
    st.title(title)
    st.caption(description)
    st.markdown(f"<p class='dashboard-scope'>数据范围：{escape(scope)}</p>", unsafe_allow_html=True)


def render_insight(title: str, body: str) -> None:
    """Render an insight inside the shared dashboard card treatment."""
    st.markdown(
        "<section class='dashboard-card'>"
        f"<strong>{escape(title)}</strong><br><span>{escape(body)}</span>"
        "</section>",
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, help_text: str) -> None:
    """Render one KPI using the common dashboard card treatment."""
    st.markdown(
        "<section class='dashboard-card'>"
        f"<div class='dashboard-kpi-label'>{escape(label)}</div>"
        f"<div class='dashboard-kpi-value'>{escape(value)}</div>"
        f"<div class='dashboard-kpi-help'>{escape(help_text)}</div>"
        "</section>",
        unsafe_allow_html=True,
    )
