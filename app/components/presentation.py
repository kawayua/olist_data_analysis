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
    "freight_revenue": "运费金额",
    "freight_rate_pct": "运费占商品金额比（%）",
    "customer_share_pct": "客户占比（%）",
    "item_revenue_share_pct": "商品金额占比（%）",
    "first_purchase_customers": "首购客户数",
    "second_purchase_customers": "二购客户数",
    "multi_purchase_customers": "多次购买客户数",
    "first_purchase_item_revenue": "首购客户商品金额",
    "repeat_customer_item_revenue": "复购客户商品金额",
    "eligible_customers": "符合观察期客户数",
    "repurchased_customers": "已复购客户数",
}

PRODUCT_CATEGORY_DISPLAY_VALUES = {
    "health_beauty": "美妆与健康",
    "watches_gifts": "钟表与礼品",
    "bed_bath_table": "床品、卫浴与餐桌",
    "sports_leisure": "运动与休闲",
    "computers_accessories": "电脑及配件",
    "furniture_decor": "家具与装饰",
    "housewares": "家居用品",
    "cool_stuff": "创意好物",
    "auto": "汽车用品",
    "toys": "玩具",
    "garden_tools": "园艺工具",
    "telephony": "通信产品",
    "baby": "母婴用品",
    "perfumery": "香水",
    "stationery": "文具",
    "fashion_bags_accessories": "时尚箱包与配饰",
    "pet_shop": "宠物用品",
    "office_furniture": "办公家具",
    "consoles_games": "游戏主机与游戏",
    "luggage_accessories": "行李箱与配件",
    "construction_tools_construction": "建筑工具",
    "electronics": "电子产品",
    "home_appliances": "家用电器",
    "small_appliances": "小家电",
    "musical_instruments": "乐器",
    "fashion_shoes": "时尚鞋履",
    "books_general_interest": "大众图书",
    "costruction_tools_garden": "园艺施工工具",
    "home_construction": "家居建材",
    "food_drink": "食品与饮料",
    "furniture_living_room": "客厅家具",
    "home_comfort_2": "家居舒适用品",
    "market_place": "综合百货",
    "audio": "音响设备",
    "drinks": "酒水饮品",
    "furniture_bedroom": "卧室家具",
    "air_conditioning": "空调",
    "kitchen_dining_laundry_garden_furniture": "厨房、餐厅与花园家具",
    "food": "食品",
    "home_comfort": "家居舒适用品",
    "books_technical": "专业图书",
    "fixed_telephony": "固定电话",
    "industry_commerce_and_business": "工商业用品",
    "construction_tools_lights": "照明施工工具",
    "fashion_male_clothing": "男装",
    "fashion_female_clothing": "女装",
    "party_supplies": "派对用品",
    "christmas_supplies": "圣诞用品",
    "cine_photo": "电影与摄影",
    "dvds_blu_ray": "DVD 与蓝光",
    "books_imported": "进口图书",
    "construction_tools_safety": "安全施工工具",
    "art": "艺术品",
    "music": "音乐",
    "fashion_underwear_beach": "内衣与泳装",
    "furniture_mattress_and_upholstery": "床垫与软体家具",
    "flowers": "鲜花",
    "diapers_and_hygiene": "纸尿裤与卫生用品",
    "fashion_sport": "运动时尚",
    "fashio_female_clothing": "女装",
    "arts_and_craftmanship": "艺术与手工艺",
    "signaling_and_security": "安防设备",
    "tablets_printing_image": "平板、打印与影像",
    "small_appliances_home_oven_and_coffee": "厨电与咖啡机",
    "fashion_childrens_clothes": "童装",
    "pc_gamer": "游戏电脑",
    "security_and_services": "安防与服务",
    "la_cuisine": "厨房用品",
    "cds_dvds_musicals": "音乐光盘与影视",
    "portable_kitchen_food_preparation": "便携厨房与食品加工",
    "unknown": "未知品类",
}

CATEGORY_DISPLAY_VALUES = {
    "customer_segment": {
        "high_value": "高价值客户",
        "potential": "潜力客户",
        "needs_attention": "需关注客户",
        "one_time_low_value": "一次低价值客户",
        "standard": "常规客户",
    },
    "interval_bucket": {
        "0_30": "0–30天",
        "31_60": "31–60天",
        "61_90": "61–90天",
        "91_180": "91–180天",
        "181_plus": "181天及以上",
    },
    "product_category": PRODUCT_CATEGORY_DISPLAY_VALUES,
    "first_purchase_category": PRODUCT_CATEGORY_DISPLAY_VALUES,
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


def display_value(column: str, value: object) -> object:
    """Return a Chinese categorical value while preserving unknown values."""
    return CATEGORY_DISPLAY_VALUES.get(column, {}).get(value, value)


def display_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready dataframe without mutating the source frame."""
    displayed = frame.copy(deep=True)
    for column in set(displayed.columns).intersection(CATEGORY_DISPLAY_VALUES):
        displayed[column] = displayed[column].map(
            lambda value, display_column=column: display_value(
                display_column, value
            )
        )
    return displayed.rename(columns=CHINESE_COLUMNS)
