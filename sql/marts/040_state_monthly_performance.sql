CREATE TABLE marts.state_monthly_performance AS
WITH delivered_orders AS (
    SELECT
        orders.order_id,
        orders.customer_key,
        orders.purchased_at,
        orders.item_revenue,
        orders.payment_value,
        customers.customer_state
    FROM warehouse.fact_orders AS orders
    JOIN raw.customers AS customers
        ON orders.source_customer_id = customers.customer_id
    WHERE orders.order_status = 'delivered'
      AND customers.customer_state IS NOT NULL
),
data_bounds AS (
    SELECT
        DATE_TRUNC('month', MIN(purchased_at))::date AS first_month,
        DATE_TRUNC('month', MAX(purchased_at))::date AS last_month
    FROM delivered_orders
)
SELECT
    DATE_TRUNC('month', orders.purchased_at)::date AS month_start,
    orders.customer_state,
    COUNT(DISTINCT orders.order_id) AS order_count,
    COUNT(DISTINCT orders.customer_key) AS customer_count,
    SUM(orders.item_revenue) AS item_revenue,
    SUM(orders.payment_value) AS payment_value,
    ROUND(
        SUM(orders.item_revenue) / COUNT(DISTINCT orders.order_id),
        2
    ) AS item_revenue_aov,
    ROUND(
        SUM(orders.payment_value) / COUNT(DISTINCT orders.order_id),
        2
    ) AS payment_aov,
    DATE_TRUNC('month', orders.purchased_at)::date > bounds.first_month
        AND DATE_TRUNC('month', orders.purchased_at)::date < bounds.last_month
        AS is_complete_month
FROM delivered_orders AS orders
CROSS JOIN data_bounds AS bounds
GROUP BY
    DATE_TRUNC('month', orders.purchased_at)::date,
    orders.customer_state,
    bounds.first_month,
    bounds.last_month;

ALTER TABLE marts.state_monthly_performance
ADD CONSTRAINT state_monthly_performance_pkey
PRIMARY KEY (month_start, customer_state);
