CREATE TABLE marts.repurchase_behavior AS
WITH delivered_orders AS (
    SELECT order_id, customer_key, purchased_at
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
data_end AS (
    SELECT MAX(purchased_at) AS as_of_timestamp
    FROM delivered_orders
),
first_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id,
        purchased_at AS first_purchase_at
    FROM delivered_orders
    ORDER BY customer_key, purchased_at, order_id
),
first_order_categories AS (
    SELECT DISTINCT
        first_orders.customer_key,
        first_orders.first_purchase_at,
        COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
        ) AS first_purchase_category
    FROM first_orders
    JOIN warehouse.fact_order_items AS items
        ON first_orders.order_id = items.order_id
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
),
next_orders AS (
    SELECT
        first_orders.customer_key,
        MIN(later_orders.purchased_at) AS next_purchase_at
    FROM first_orders
    LEFT JOIN delivered_orders AS later_orders
        ON first_orders.customer_key = later_orders.customer_key
       AND later_orders.purchased_at > first_orders.first_purchase_at
    GROUP BY first_orders.customer_key
),
horizons AS (
    SELECT horizon_days
    FROM (VALUES (30), (60), (90)) AS horizon_values(horizon_days)
)
SELECT
    categories.first_purchase_category,
    horizons.horizon_days,
    COUNT(*) FILTER (
        WHERE data_end.as_of_timestamp::date >= categories.first_purchase_at::date
            + horizons.horizon_days * INTERVAL '1 day'
    ) AS eligible_customers,
    COUNT(*) FILTER (
        WHERE data_end.as_of_timestamp::date >= categories.first_purchase_at::date
            + horizons.horizon_days * INTERVAL '1 day'
          AND next_orders.next_purchase_at <= categories.first_purchase_at
            + horizons.horizon_days * INTERVAL '1 day'
    ) AS repurchased_customers,
    ROUND(
        COUNT(*) FILTER (
            WHERE data_end.as_of_timestamp::date >= categories.first_purchase_at::date
                + horizons.horizon_days * INTERVAL '1 day'
              AND next_orders.next_purchase_at <= categories.first_purchase_at
                + horizons.horizon_days * INTERVAL '1 day'
        )::numeric
        / NULLIF(
            COUNT(*) FILTER (
                WHERE data_end.as_of_timestamp::date >= categories.first_purchase_at::date
                    + horizons.horizon_days * INTERVAL '1 day'
            ),
            0
        ) * 100,
        3
    ) AS repurchase_rate_pct
FROM first_order_categories AS categories
JOIN next_orders
    ON categories.customer_key = next_orders.customer_key
CROSS JOIN data_end
CROSS JOIN horizons
GROUP BY categories.first_purchase_category, horizons.horizon_days;

ALTER TABLE marts.repurchase_behavior
ADD CONSTRAINT repurchase_behavior_pkey
PRIMARY KEY (first_purchase_category, horizon_days);

CREATE TABLE marts.repurchase_intervals AS
WITH delivered_orders AS (
    SELECT order_id, customer_key, purchased_at
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
first_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        purchased_at AS first_purchase_at
    FROM delivered_orders
    ORDER BY customer_key, purchased_at, order_id
),
next_orders AS (
    SELECT
        first_orders.customer_key,
        MIN(later_orders.purchased_at) AS next_purchase_at,
        first_orders.first_purchase_at
    FROM first_orders
    JOIN delivered_orders AS later_orders
        ON first_orders.customer_key = later_orders.customer_key
       AND later_orders.purchased_at > first_orders.first_purchase_at
    GROUP BY first_orders.customer_key, first_orders.first_purchase_at
),
bucketed AS (
    SELECT
        CASE
            WHEN next_purchase_at <= first_purchase_at + INTERVAL '30 days' THEN '0_30'
            WHEN next_purchase_at <= first_purchase_at + INTERVAL '60 days' THEN '31_60'
            WHEN next_purchase_at <= first_purchase_at + INTERVAL '90 days' THEN '61_90'
            WHEN next_purchase_at <= first_purchase_at + INTERVAL '180 days' THEN '91_180'
            ELSE '181_plus'
        END AS interval_bucket
    FROM next_orders
)
SELECT
    interval_bucket,
    COUNT(*) AS customer_count
FROM bucketed
GROUP BY interval_bucket;

ALTER TABLE marts.repurchase_intervals
ADD CONSTRAINT repurchase_intervals_pkey PRIMARY KEY (interval_bucket);
