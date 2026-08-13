"""Chinese display labels for dashboard-facing data."""

import pandas as pd

CHINESE_COLUMNS = {
    "item_revenue": "商品金额",
    "payment_value": "支付金额",
    "item_revenue_aov": "商品金额客单价",
    "order_count": "订单数",
    "customer_count": "客户数",
    "customer_state": "客户所在州",
    "product_category": "商品品类",
    "customer_segment": "客户分群",
    "delivery_status": "履约状态",
    "average_review_score": "平均评分",
    "delayed_delivery_rate_pct": "延迟送达率（%）",
    "average_delivery_days": "平均配送天数",
    "median_delivery_days": "配送天数中位数",
    "first_purchase_customer_count": "首购客户数",
    "eligible_first_purchase_customer_count": "符合条件的首购客户数",
    "eligible_first_purchase_customers": "符合条件的首购客户数",
    "repurchased_first_purchase_customers": "已复购首购客户数",
    "repurchase_rate_90d_pct": "90天复购率（%）",
    "month_start": "月份",
    "retention_rate_pct": "留存率（%）",
    "active_customers": "购买用户数",
    "item_revenue_mom_pct": "商品金额环比（%）",
    "active_customers_mom_pct": "购买用户环比（%）",
    "order_count_mom_pct": "订单环比（%）",
    "item_revenue_aov_mom_pct": "客单价环比（%）",
    "new_customer_item_revenue": "新客商品金额",
    "returning_customer_item_revenue": "老客商品金额",
    "first_purchase_category": "首购品类",
    "horizon_days": "观察天数",
    "repurchase_rate_pct": "复购率（%）",
    "interval_bucket": "二购间隔",
    "delivery_delay_bucket": "相对预计送达分组",
    "average_delivery_vs_estimate_days": "相对预计送达天数",
    "average_frequency_orders": "平均购买次数",
    "average_monetary_item_revenue": "平均客户商品金额",
    "average_recency_days": "平均最近购买间隔（天）",
}


def summarize_state_performance(frame: pd.DataFrame) -> pd.Series:
    """Aggregate state rows while preserving the denominators of rate metrics."""
    summary = frame.sum(numeric_only=True)
    order_count = summary.get("order_count", 0)
    eligible_customers = summary.get("eligible_first_purchase_customers", 0)
    delayed_orders = (
        frame["order_count"] * frame["delayed_delivery_rate_pct"] / 100
    ).sum()
    summary["delayed_delivery_rate_pct"] = (
        delayed_orders / order_count * 100 if order_count else None
    )
    summary["repurchase_rate_90d_pct"] = (
        summary.get("repurchased_first_purchase_customers", 0)
        / eligible_customers
        * 100
        if eligible_customers
        else None
    )
    return summary


def display_label(column: str) -> str:
    """Return the Chinese label for a known analytical column."""
    return CHINESE_COLUMNS.get(column, column)


def display_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready dataframe without mutating the source frame."""
    return frame.rename(columns=CHINESE_COLUMNS)
