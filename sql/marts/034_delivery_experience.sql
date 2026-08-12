CREATE TABLE marts.delivery_experience AS
WITH delivered_orders AS (
    SELECT
        orders.order_id,
        orders.customer_key,
        orders.purchased_at,
        orders.delivered_at,
        orders.estimated_delivery_at,
        orders.is_delivery_late
    FROM warehouse.fact_orders AS orders
    WHERE orders.order_status = 'delivered'
),
customer_first_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id
    FROM delivered_orders
    ORDER BY customer_key, purchased_at, order_id
),
order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS average_review_score
    FROM warehouse.fact_reviews
    GROUP BY order_id
),
classified_orders AS (
    SELECT
        orders.*,
        CASE
            WHEN orders.is_delivery_late THEN 'late'
            ELSE 'on_time'
        END AS delivery_status,
        EXTRACT(EPOCH FROM (orders.delivered_at - orders.purchased_at)) / 86400.0
            AS delivery_days,
        EXTRACT(EPOCH FROM (orders.delivered_at - orders.estimated_delivery_at))
            / 86400.0 AS delivery_vs_estimate_days,
        reviews.average_review_score
    FROM delivered_orders AS orders
    LEFT JOIN order_reviews AS reviews
        ON orders.order_id = reviews.order_id
)
SELECT
    orders.delivery_status,
    COUNT(*) AS order_count,
    COUNT(DISTINCT orders.customer_key) AS customer_count,
    ROUND(AVG(orders.is_delivery_late::integer) * 100, 3) AS delayed_delivery_rate_pct,
    ROUND(AVG(orders.delivery_days), 3) AS average_delivery_days,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY orders.delivery_days)
        AS median_delivery_days,
    ROUND(AVG(orders.delivery_vs_estimate_days), 3) AS average_delivery_vs_estimate_days,
    ROUND(AVG(orders.average_review_score), 3) AS average_review_score,
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
FROM classified_orders AS orders
JOIN customer_first_orders AS first_orders
    ON orders.customer_key = first_orders.customer_key
JOIN marts.customer_360 AS customer_360
    ON orders.customer_key = customer_360.customer_key
GROUP BY orders.delivery_status;

ALTER TABLE marts.delivery_experience
ADD CONSTRAINT delivery_experience_pkey PRIMARY KEY (delivery_status);
