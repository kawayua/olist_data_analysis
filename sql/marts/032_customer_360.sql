CREATE TABLE marts.customer_360 AS
WITH delivered_orders AS (
    SELECT
        order_id,
        customer_key,
        purchased_at,
        delivered_at,
        item_revenue,
        freight_revenue,
        payment_value
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
data_end AS (
    SELECT MAX(purchased_at) AS as_of_timestamp
    FROM delivered_orders
),
customer_orders AS (
    SELECT
        customer_key,
        MIN(purchased_at) AS first_purchase_at,
        MAX(purchased_at) AS last_purchase_at,
        COUNT(*) AS frequency_orders,
        SUM(item_revenue) AS monetary_item_revenue,
        SUM(freight_revenue) AS freight_revenue,
        SUM(payment_value) AS payment_value,
        AVG(
            EXTRACT(EPOCH FROM (delivered_at - purchased_at)) / 86400.0
        ) FILTER (WHERE delivered_at IS NOT NULL) AS avg_delivery_days
    FROM delivered_orders
    GROUP BY customer_key
),
customer_categories AS (
    SELECT
        orders.customer_key,
        COUNT(DISTINCT COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
        )) AS distinct_category_count
    FROM delivered_orders AS orders
    JOIN warehouse.fact_order_items AS items
        ON orders.order_id = items.order_id
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
    GROUP BY orders.customer_key
),
customer_reviews AS (
    SELECT
        orders.customer_key,
        AVG(reviews.review_score) AS avg_review_score
    FROM delivered_orders AS orders
    JOIN warehouse.fact_reviews AS reviews
        ON orders.order_id = reviews.order_id
    GROUP BY orders.customer_key
),
repurchase_labels AS (
    SELECT
        customers.customer_key,
        BOOL_OR(
            later_orders.purchased_at > customers.first_purchase_at
            AND later_orders.purchased_at
                <= customers.first_purchase_at + INTERVAL '90 days'
        ) AS repurchased_within_90d
    FROM customer_orders AS customers
    JOIN delivered_orders AS later_orders
        ON customers.customer_key = later_orders.customer_key
    GROUP BY customers.customer_key
),
cutoffs AS (
    SELECT
        percentile_cont(0.25) WITHIN GROUP (
            ORDER BY data_end.as_of_timestamp::date - orders.last_purchase_at::date
        ) AS recency_p25,
        percentile_cont(0.50) WITHIN GROUP (
            ORDER BY data_end.as_of_timestamp::date - orders.last_purchase_at::date
        ) AS recency_p50,
        percentile_cont(0.75) WITHIN GROUP (
            ORDER BY data_end.as_of_timestamp::date - orders.last_purchase_at::date
        ) AS recency_p75,
        percentile_cont(0.25) WITHIN GROUP (
            ORDER BY orders.monetary_item_revenue
        ) AS monetary_p25,
        percentile_cont(0.50) WITHIN GROUP (
            ORDER BY orders.monetary_item_revenue
        ) AS monetary_p50,
        percentile_cont(0.75) WITHIN GROUP (
            ORDER BY orders.monetary_item_revenue
        ) AS monetary_p75
    FROM customer_orders AS orders
    CROSS JOIN data_end
),
scored AS (
    SELECT
        orders.*,
        data_end.as_of_timestamp AS snapshot_at,
        data_end.as_of_timestamp::date - orders.last_purchase_at::date AS recency_days,
        CASE
            WHEN data_end.as_of_timestamp::date - orders.last_purchase_at::date <= cutoffs.recency_p25 THEN 4
            WHEN data_end.as_of_timestamp::date - orders.last_purchase_at::date <= cutoffs.recency_p50 THEN 3
            WHEN data_end.as_of_timestamp::date - orders.last_purchase_at::date <= cutoffs.recency_p75 THEN 2
            ELSE 1
        END AS r_score,
        CASE
            WHEN orders.frequency_orders = 1 THEN 1
            WHEN orders.frequency_orders = 2 THEN 2
            ELSE 3
        END AS f_score,
        CASE
            WHEN orders.monetary_item_revenue <= cutoffs.monetary_p25 THEN 1
            WHEN orders.monetary_item_revenue <= cutoffs.monetary_p50 THEN 2
            WHEN orders.monetary_item_revenue <= cutoffs.monetary_p75 THEN 3
            ELSE 4
        END AS m_score
    FROM customer_orders AS orders
    CROSS JOIN data_end
    CROSS JOIN cutoffs
),
segmented AS (
    SELECT
        scored.*,
        CASE
            WHEN r_score >= 3 AND f_score >= 2 AND m_score >= 3 THEN 'high_value'
            WHEN r_score >= 3 AND f_score = 1 AND m_score >= 3 THEN 'potential'
            WHEN r_score <= 2 AND m_score >= 3 THEN 'needs_attention'
            WHEN f_score = 1 AND m_score <= 2 THEN 'one_time_low_value'
            ELSE 'standard'
        END AS customer_segment
    FROM scored
)
SELECT
    segmented.customer_key,
    segmented.snapshot_at,
    segmented.snapshot_at AS feature_available_at,
    segmented.first_purchase_at,
    segmented.last_purchase_at,
    segmented.recency_days,
    segmented.frequency_orders,
    segmented.monetary_item_revenue,
    segmented.freight_revenue,
    segmented.payment_value,
    categories.distinct_category_count,
    reviews.avg_review_score,
    segmented.avg_delivery_days,
    segmented.r_score,
    segmented.f_score,
    segmented.m_score,
    segmented.customer_segment,
    data_end.as_of_timestamp::date >= segmented.first_purchase_at::date
        + INTERVAL '90 days'
        AS eligible_for_90d,
    CASE
        WHEN data_end.as_of_timestamp::date < segmented.first_purchase_at::date
            + INTERVAL '90 days'
            THEN NULL
        ELSE labels.repurchased_within_90d
    END AS repurchased_within_90d
FROM segmented
CROSS JOIN data_end
JOIN repurchase_labels AS labels
    ON segmented.customer_key = labels.customer_key
LEFT JOIN customer_categories AS categories
    ON segmented.customer_key = categories.customer_key
LEFT JOIN customer_reviews AS reviews
    ON segmented.customer_key = reviews.customer_key;

ALTER TABLE marts.customer_360
ADD CONSTRAINT customer_360_pkey PRIMARY KEY (customer_key);

ALTER TABLE marts.customer_360
ADD CONSTRAINT customer_360_customer_key_fkey
FOREIGN KEY (customer_key)
REFERENCES warehouse.dim_customer (customer_key);
