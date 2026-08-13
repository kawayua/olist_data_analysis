CREATE TABLE marts.state_performance AS
WITH delivered_orders AS (
    SELECT
        orders.order_id,
        orders.customer_key,
        orders.purchased_at,
        orders.item_revenue,
        orders.payment_value,
        orders.is_delivery_late,
        orders.delivered_at,
        orders.estimated_delivery_at,
        customers.customer_state
    FROM warehouse.fact_orders AS orders
    JOIN raw.customers AS customers
        ON orders.source_customer_id = customers.customer_id
    WHERE orders.order_status = 'delivered'
      AND customers.customer_state IS NOT NULL
),
order_reviews AS (
    SELECT order_id, AVG(review_score) AS average_review_score
    FROM warehouse.fact_reviews
    GROUP BY order_id
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
    ROUND(
        AVG(EXTRACT(EPOCH FROM (orders.delivered_at - orders.purchased_at)) / 86400.0),
        3
    ) AS average_delivery_days,
    ROUND(AVG(reviews.average_review_score), 3) AS average_review_score,
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
LEFT JOIN order_reviews AS reviews
    ON orders.order_id = reviews.order_id
JOIN first_delivered_orders AS first_orders
    ON orders.customer_key = first_orders.customer_key
JOIN marts.customer_360 AS customer_360
    ON orders.customer_key = customer_360.customer_key
GROUP BY orders.customer_state;

ALTER TABLE marts.state_performance
ADD CONSTRAINT state_performance_pkey PRIMARY KEY (customer_state);
