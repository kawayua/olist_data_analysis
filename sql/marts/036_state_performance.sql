CREATE TABLE marts.state_performance AS
WITH delivered_orders AS (
    SELECT
        orders.order_id,
        orders.customer_key,
        orders.purchased_at,
        orders.item_revenue,
        orders.payment_value,
        orders.is_delivery_late,
        customers.customer_state
    FROM warehouse.fact_orders AS orders
    JOIN raw.customers AS customers
        ON orders.source_customer_id = customers.customer_id
    WHERE orders.order_status = 'delivered'
      AND customers.customer_state IS NOT NULL
),
first_delivered_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id
    FROM delivered_orders
    ORDER BY customer_key, purchased_at, order_id
)
SELECT
    orders.customer_state,
    COUNT(DISTINCT orders.order_id) AS order_count,
    COUNT(DISTINCT orders.customer_key) AS customer_count,
    SUM(orders.item_revenue) AS item_revenue,
    SUM(orders.payment_value) AS payment_value,
    ROUND(SUM(orders.item_revenue) / COUNT(DISTINCT orders.order_id), 2)
        AS item_revenue_aov,
    ROUND(AVG(orders.is_delivery_late::integer) * 100, 3)
        AS delayed_delivery_rate_pct,
    COUNT(DISTINCT orders.customer_key) FILTER (
        WHERE first_orders.order_id = orders.order_id
          AND customer_360.eligible_for_90d
    ) AS eligible_first_purchase_customers,
    COUNT(DISTINCT orders.customer_key) FILTER (
        WHERE first_orders.order_id = orders.order_id
          AND customer_360.eligible_for_90d
          AND customer_360.repurchased_within_90d
    ) AS repurchased_first_purchase_customers,
    ROUND(
        COUNT(DISTINCT orders.customer_key) FILTER (
            WHERE first_orders.order_id = orders.order_id
              AND customer_360.eligible_for_90d
              AND customer_360.repurchased_within_90d
        )::numeric
        / NULLIF(
            COUNT(DISTINCT orders.customer_key) FILTER (
                WHERE first_orders.order_id = orders.order_id
                  AND customer_360.eligible_for_90d
            ),
            0
        ) * 100,
        3
    ) AS repurchase_rate_90d_pct
FROM delivered_orders AS orders
JOIN first_delivered_orders AS first_orders
    ON orders.customer_key = first_orders.customer_key
JOIN marts.customer_360 AS customer_360
    ON orders.customer_key = customer_360.customer_key
GROUP BY orders.customer_state;

ALTER TABLE marts.state_performance
ADD CONSTRAINT state_performance_pkey PRIMARY KEY (customer_state);
