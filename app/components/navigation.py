"""Shared floating navigation for the dashboard analysis pages."""

import streamlit as st

NAVIGATION_PAGES = (
    ("pages/1_经营总览.py", "经营总览"),
    ("pages/2_增长诊断.py", "增长诊断"),
    ("pages/3_留存复购.py", "留存复购"),
    ("pages/4_客户价值.py", "客户价值"),
    ("pages/5_商品与履约.py", "商品与履约"),
    ("pages/6_营销ROI模拟器.py", "营销ROI"),
    ("pages/7_AI分析助手.py", "AI分析助手"),
)


def render_navigation() -> None:
    """Render links for the dashboard's analysis pages."""
    with st.container(key="floating-navigation"):
        for column, (path, label) in zip(
            st.columns(len(NAVIGATION_PAGES), gap="small"), NAVIGATION_PAGES, strict=True
        ):
            with column:
                st.page_link(path, label=label)
