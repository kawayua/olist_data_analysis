"""Shared floating navigation for the dashboard analysis pages."""

import streamlit as st

NAVIGATION_PAGES = (
    ("pages/1_经营总览.py", "经营总览"),
    ("pages/2_增长诊断.py", "增长诊断"),
    ("pages/3_留存复购.py", "留存复购"),
    ("pages/4_客户价值.py", "客户价值"),
    ("pages/5_商品与履约.py", "商品与履约"),
)


def render_navigation() -> None:
    """Render links for the dashboard's five analysis pages."""
    with st.container(key="floating-navigation"):
        for path, label in NAVIGATION_PAGES:
            st.page_link(path, label=label, use_container_width=True)
