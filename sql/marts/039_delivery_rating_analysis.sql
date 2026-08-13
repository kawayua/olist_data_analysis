CREATE TABLE marts.delivery_rating_analysis AS
WITH delivered_orders AS (
    SELECT
        orders.order_id,
        EXTRACT(EPOCH FROM (orders.delivered_at - orders.estimated_delivery_at))
            / 86400.0 AS delivery_vs_estimate_days
    FROM warehouse.fact_orders AS orders
    WHERE orders.order_status = 'delivered'
),
order_reviews AS (
    SELECT order_id, AVG(review_score) AS average_review_score
    FROM warehouse.fact_reviews
    GROUP BY order_id
),
bucketed_orders AS (
    SELECT
        CASE
            WHEN orders.delivery_vs_estimate_days <= -7 THEN '提前7天及以上'
            WHEN orders.delivery_vs_estimate_days <= -1 THEN '提前1至6天'
            WHEN orders.delivery_vs_estimate_days <= 0 THEN '按预计送达'
            WHEN orders.delivery_vs_estimate_days <= 3 THEN '延迟1至3天'
            WHEN orders.delivery_vs_estimate_days <= 7 THEN '延迟4至7天'
            ELSE '延迟8天及以上'
        END AS delivery_delay_bucket,
        orders.delivery_vs_estimate_days,
        reviews.average_review_score
    FROM delivered_orders AS orders
    JOIN order_reviews AS reviews
        ON orders.order_id = reviews.order_id
)
SELECT
    delivery_delay_bucket,
    COUNT(*) AS order_count,
    ROUND(AVG(delivery_vs_estimate_days), 3) AS average_delivery_vs_estimate_days,
    ROUND(AVG(average_review_score), 3) AS average_review_score
FROM bucketed_orders
GROUP BY delivery_delay_bucket;

ALTER TABLE marts.delivery_rating_analysis
ADD CONSTRAINT delivery_rating_analysis_pkey PRIMARY KEY (delivery_delay_bucket);
