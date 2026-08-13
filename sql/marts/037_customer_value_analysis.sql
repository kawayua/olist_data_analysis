CREATE TABLE marts.customer_value_analysis AS
WITH segment_totals AS (
    SELECT
        customer_segment,
        COUNT(*) AS customer_count,
        SUM(monetary_item_revenue) AS item_revenue,
        AVG(recency_days) AS average_recency_days,
        AVG(frequency_orders) AS average_frequency_orders,
        AVG(monetary_item_revenue) AS average_monetary_item_revenue,
        COUNT(*) FILTER (WHERE frequency_orders = 1) AS first_purchase_customers,
        COUNT(*) FILTER (WHERE frequency_orders = 2) AS second_purchase_customers,
        COUNT(*) FILTER (WHERE frequency_orders >= 3) AS multi_purchase_customers
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
    totals.customer_segment,
    totals.customer_count,
    ROUND(totals.customer_count::numeric / overall.all_customers * 100, 3)
        AS customer_share_pct,
    totals.item_revenue,
    ROUND(totals.item_revenue / overall.all_item_revenue * 100, 3)
        AS item_revenue_share_pct,
    ROUND(totals.average_recency_days, 3) AS average_recency_days,
    ROUND(totals.average_frequency_orders, 3) AS average_frequency_orders,
    ROUND(totals.average_monetary_item_revenue, 2)
        AS average_monetary_item_revenue,
    totals.first_purchase_customers,
    totals.second_purchase_customers,
    totals.multi_purchase_customers
FROM segment_totals AS totals
CROSS JOIN overall;

ALTER TABLE marts.customer_value_analysis
ADD CONSTRAINT customer_value_analysis_pkey PRIMARY KEY (customer_segment);
