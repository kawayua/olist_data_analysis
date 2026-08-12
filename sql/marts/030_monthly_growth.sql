CREATE TABLE marts.monthly_growth AS
WITH delivered_orders AS (
    SELECT
        order_id,
        customer_key,
        purchased_at,
        item_revenue,
        payment_value
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
customer_first_purchase AS (
    SELECT
        customer_key,
        DATE_TRUNC('month', MIN(purchased_at))::date AS first_purchase_month
    FROM delivered_orders
    GROUP BY customer_key
),
data_bounds AS (
    SELECT
        DATE_TRUNC('month', MIN(purchased_at))::date AS first_month,
        DATE_TRUNC('month', MAX(purchased_at))::date AS last_month
    FROM delivered_orders
),
calendar AS (
    SELECT months.month_start::date AS month_start
    FROM data_bounds
    CROSS JOIN LATERAL generate_series(
        data_bounds.first_month::timestamp,
        data_bounds.last_month::timestamp,
        INTERVAL '1 month'
    ) AS months(month_start)
),
monthly_orders AS (
    SELECT
        DATE_TRUNC('month', orders.purchased_at)::date AS month_start,
        SUM(orders.item_revenue) AS item_revenue,
        SUM(orders.payment_value) AS payment_value,
        COUNT(DISTINCT orders.order_id) AS order_count,
        COUNT(DISTINCT orders.customer_key) AS active_customers,
        COUNT(DISTINCT orders.customer_key) FILTER (
            WHERE first_purchase.first_purchase_month
                = DATE_TRUNC('month', orders.purchased_at)::date
        ) AS new_customers,
        COUNT(DISTINCT orders.customer_key) FILTER (
            WHERE first_purchase.first_purchase_month
                < DATE_TRUNC('month', orders.purchased_at)::date
        ) AS returning_customers,
        SUM(orders.item_revenue) FILTER (
            WHERE first_purchase.first_purchase_month
                = DATE_TRUNC('month', orders.purchased_at)::date
        ) AS new_customer_item_revenue,
        SUM(orders.item_revenue) FILTER (
            WHERE first_purchase.first_purchase_month
                < DATE_TRUNC('month', orders.purchased_at)::date
        ) AS returning_customer_item_revenue
    FROM delivered_orders AS orders
    JOIN customer_first_purchase AS first_purchase
        ON orders.customer_key = first_purchase.customer_key
    GROUP BY DATE_TRUNC('month', orders.purchased_at)::date
)
SELECT
    calendar.month_start,
    COALESCE(monthly.item_revenue, 0::numeric) AS item_revenue,
    COALESCE(monthly.payment_value, 0::numeric) AS payment_value,
    COALESCE(monthly.order_count, 0) AS order_count,
    COALESCE(monthly.active_customers, 0) AS active_customers,
    COALESCE(monthly.new_customers, 0) AS new_customers,
    COALESCE(monthly.returning_customers, 0) AS returning_customers,
    COALESCE(monthly.new_customer_item_revenue, 0::numeric)
        AS new_customer_item_revenue,
    COALESCE(monthly.returning_customer_item_revenue, 0::numeric)
        AS returning_customer_item_revenue,
    CASE
        WHEN COALESCE(monthly.order_count, 0) = 0 THEN NULL
        ELSE ROUND(monthly.item_revenue / monthly.order_count, 2)
    END AS item_revenue_aov,
    CASE
        WHEN COALESCE(monthly.order_count, 0) = 0 THEN NULL
        ELSE ROUND(monthly.payment_value / monthly.order_count, 2)
    END AS payment_aov,
    CASE
        WHEN LAG(COALESCE(monthly.item_revenue, 0::numeric)) OVER month_window = 0
            THEN NULL
        ELSE ROUND(
            (
                COALESCE(monthly.item_revenue, 0::numeric)
                / LAG(COALESCE(monthly.item_revenue, 0::numeric)) OVER month_window - 1
            ) * 100,
            3
        )
    END AS item_revenue_mom_pct,
    calendar.month_start > bounds.first_month
        AND calendar.month_start < bounds.last_month AS is_complete_month
FROM calendar
CROSS JOIN data_bounds AS bounds
LEFT JOIN monthly_orders AS monthly
    ON calendar.month_start = monthly.month_start
WINDOW month_window AS (ORDER BY calendar.month_start);

ALTER TABLE marts.monthly_growth
ADD CONSTRAINT monthly_growth_pkey PRIMARY KEY (month_start);
