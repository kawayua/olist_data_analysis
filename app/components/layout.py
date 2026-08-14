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
        [data-testid="stMain"] .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewContainer"] .main .block-container {
            width: 100% !important; max-width: none !important;
            padding-left: clamp(1.5rem, 4vw, 6rem) !important;
            padding-right: clamp(1.5rem, 4vw, 6rem) !important;
        }
.st-key-floating-navigation {
    position: sticky; top: 12px; z-index: 999;
    left: 50%; transform: translateX(-50%);
    width: min(960px, calc(100vw - 8rem)) !important;
    margin: 48px 0 1rem;
}

.st-key-floating-navigation [data-testid="stHorizontalBlock"] {
    display: flex; flex-wrap: nowrap; justify-content: center; gap: 0.5rem;
    width: min(960px, calc(100vw - 8rem)) !important;
    max-width: none !important;
    padding: 0.65rem;
    overflow-x: hidden;
    background: rgba(255, 255, 255, 0.76);
    border: 1px solid #e5eaf1;
    border-radius: 28px;
    box-shadow: 0 8px 24px rgba(20, 42, 74, 0.12);
    backdrop-filter: blur(12px);
}
.st-key-floating-navigation [data-testid="stColumn"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
}
        .st-key-floating-navigation [data-testid="stPageLink-NavLink"] {
            flex: 1 1 0; min-height: 3.1rem; border-radius: 22px;
            color: #355070; font-size: 1.25rem; font-weight: 650;
            padding: 0.65rem 0.75rem; text-align: center; white-space: nowrap;
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
