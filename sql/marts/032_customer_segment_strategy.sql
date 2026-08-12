CREATE TABLE marts.customer_segment_strategy AS
WITH segment_rules AS (
    SELECT *
    FROM (VALUES
        (
            'high_value',
            '近期购买，至少两笔订单，且商品金额位于较高分位。',
            '优先维护：会员权益、服务保障与个性化复购推荐。'
        ),
        (
            'potential',
            '近期购买、商品金额较高，但仅有一笔订单。',
            '优先促成第二单：首购后触达、二单券和相似品类推荐。'
        ),
        (
            'needs_attention',
            '商品金额较高，但最近购买时间较久。',
            '分层召回：小规模测试优惠强度，并控制触达成本。'
        ),
        (
            'one_time_low_value',
            '仅有一笔订单，且商品金额较低。',
            '低成本自动化触达；不优先投入人工运营预算。'
        ),
        (
            'standard',
            '未落入上述四类明确策略规则。',
            '持续监控，待更多行为数据后再细分。'
        )
    ) AS rules(customer_segment, segment_definition, recommended_action)
),
segment_totals AS (
    SELECT
        customer_segment,
        COUNT(*) AS customer_count,
        SUM(monetary_item_revenue) AS item_revenue
    FROM marts.customer_360
    GROUP BY customer_segment
),
overall AS (
    SELECT
        SUM(customer_count) AS all_customers,
        SUM(item_revenue) AS all_item_revenue
    FROM segment_totals
)
SELECT
    rules.customer_segment,
    rules.segment_definition,
    rules.recommended_action,
    COALESCE(totals.customer_count, 0) AS customer_count,
    ROUND(
        COALESCE(totals.customer_count, 0)::numeric / overall.all_customers * 100,
        3
    ) AS customer_share_pct,
    COALESCE(totals.item_revenue, 0::numeric) AS item_revenue,
    ROUND(
        COALESCE(totals.item_revenue, 0::numeric) / overall.all_item_revenue * 100,
        3
    ) AS item_revenue_share_pct,
    'Frequency 中约 97 percent 的客户只有一笔订单；F 分数采用 1 / 2 / 3+ 的稳定业务规则，不能被解释为细粒度频率差异。'
        AS frequency_limitation
FROM segment_rules AS rules
LEFT JOIN segment_totals AS totals
    ON rules.customer_segment = totals.customer_segment
CROSS JOIN overall;

ALTER TABLE marts.customer_segment_strategy
ADD CONSTRAINT customer_segment_strategy_pkey PRIMARY KEY (customer_segment);
