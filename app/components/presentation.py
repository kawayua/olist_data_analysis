"""Chinese display labels for dashboard-facing data."""

import pandas as pd

CHINESE_COLUMNS = {
    "item_revenue": "商品金额",
    "order_count": "订单数",
    "customer_count": "客户数",
    "customer_state": "客户所在州",
    "product_category": "商品品类",
    "customer_segment": "客户分群",
    "delivery_status": "履约状态",
    "average_review_score": "平均评分",
    "month_start": "月份",
    "retention_rate_pct": "留存率（%）",
}


def display_label(column: str) -> str:
    """Return the Chinese label for a known analytical column."""
    return CHINESE_COLUMNS.get(column, column)


def display_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready dataframe without mutating the source frame."""
    return frame.rename(columns=CHINESE_COLUMNS)
