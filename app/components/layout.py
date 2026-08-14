"""Shared visual layout primitives for Streamlit dashboard pages."""

from html import escape

import streamlit as st


def apply_dashboard_theme() -> None:
    """Inject the dashboard's shared background, cards, and responsive spacing."""
    st.markdown(
        """
        <style>
        .stApp { background: #f6f8fb; }
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: none; padding-left: 3rem; padding-right: 3rem;
        }
        .st-key-floating-navigation {
            position: sticky; top: 48px; z-index: 999;
            display: flex; justify-content: center;
            width: 100%; margin: 0 0 1rem;
        }
        .st-key-floating-navigation [data-testid="stHorizontalBlock"] {
            display: flex; flex-wrap: nowrap; justify-content: center; gap: 0.35rem;
            width: fit-content; max-width: calc(100vw - 2rem); padding: 0.45rem;
            background: rgba(255, 255, 255, 0.76); border: 1px solid #e5eaf1;
            border-radius: 28px; box-shadow: 0 8px 24px rgba(20, 42, 74, 0.12);
            backdrop-filter: blur(12px);
        }
        .st-key-floating-navigation [data-testid="stPageLink-NavLink"] {
            flex: 0 1 auto; min-height: 2.5rem; border-radius: 20px;
            color: #355070; font-weight: 600;
            transition: background-color 180ms ease, color 180ms ease;
        }
        .st-key-floating-navigation [data-testid="stPageLink-NavLink"]:hover {
            background: #edf3fa; color: #172b4d;
        }
        .st-key-floating-navigation [data-testid="stPageLink-NavLink"]:focus-visible {
            outline: 3px solid #d49231; outline-offset: 2px;
        }
        .st-key-floating-navigation [data-testid="stPageLink-NavLink"][aria-current="page"] {
            background: #172b4d; color: #ffffff;
        }
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
            .st-key-floating-navigation { top: 16px; }
            [data-testid="stAppViewContainer"] .main .block-container {
                padding-left: 1rem; padding-right: 1rem;
            }
            .st-key-floating-navigation [data-testid="stHorizontalBlock"] {
                max-width: calc(100vw - 1rem); flex-wrap: wrap;
            }
            .st-key-floating-navigation [data-testid="stPageLink-NavLink"] { flex: 1 1 8.5rem; justify-content: center; }
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
