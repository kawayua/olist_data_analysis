CREATE TABLE marts.delivery_order_analysis AS
WITH delivered_orders AS (
    SELECT
        order_id,
        customer_key,
        purchased_at,
        delivered_at,
        estimated_delivery_at,
        is_delivery_late
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
first_delivered_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id
    FROM delivered_orders
    ORDER BY customer_key, purchased_at, order_id
),
order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM warehouse.fact_reviews
    GROUP BY order_id
)
SELECT
    orders.order_id,
    orders.customer_key,
    CASE
        WHEN orders.is_delivery_late THEN 'late'
        ELSE 'on_time'
    END AS delivery_status,
    EXTRACT(EPOCH FROM (orders.delivered_at - orders.purchased_at)) / 86400.0
        AS delivery_days,
    EXTRACT(EPOCH FROM (orders.delivered_at - orders.estimated_delivery_at)) / 86400.0
        AS delivery_vs_estimate_days,
    reviews.review_score,
    first_orders.order_id IS NOT NULL AS is_first_delivered_order,
    CASE
        WHEN first_orders.order_id IS NOT NULL THEN customer_360.eligible_for_90d
    END AS eligible_for_90d,
    CASE
        WHEN first_orders.order_id IS NOT NULL AND customer_360.eligible_for_90d
            THEN customer_360.repurchased_within_90d
    END AS repurchased_within_90d
FROM delivered_orders AS orders
LEFT JOIN first_delivered_orders AS first_orders
    ON orders.customer_key = first_orders.customer_key
   AND orders.order_id = first_orders.order_id
JOIN marts.customer_360 AS customer_360
    ON orders.customer_key = customer_360.customer_key
LEFT JOIN order_reviews AS reviews
    ON orders.order_id = reviews.order_id;

ALTER TABLE marts.delivery_order_analysis
ADD CONSTRAINT delivery_order_analysis_pkey PRIMARY KEY (order_id);
