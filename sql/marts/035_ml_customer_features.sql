CREATE TABLE marts.ml_customer_features AS
WITH delivered_orders AS (
    SELECT
        order_id,
        customer_key,
        purchased_at,
        delivered_at,
        estimated_delivery_at,
        approved_at,
        delivered_to_carrier_at,
        customer_state,
        is_delivery_late,
        item_count,
        item_revenue,
        freight_revenue,
        payment_value
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
      AND delivered_at IS NOT NULL
),
first_delivered_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id,
        delivered_at AS prediction_time,
        purchased_at AS first_order_purchased_at,
        item_count AS first_order_item_count,
        item_revenue AS first_order_item_revenue,
        freight_revenue AS first_order_freight_revenue,
        payment_value AS first_order_payment_value,
        customer_state,
        is_delivery_late AS first_order_is_late,
        EXTRACT(EPOCH FROM (delivered_at - purchased_at)) / 86400.0
            AS first_order_delivery_days,
        EXTRACT(EPOCH FROM (estimated_delivery_at - purchased_at)) / 86400.0
            AS first_order_estimated_delivery_days,
        EXTRACT(EPOCH FROM (delivered_at - estimated_delivery_at)) / 86400.0
            AS first_order_delivery_vs_estimate_days,
        EXTRACT(MONTH FROM purchased_at)::integer AS first_order_purchase_month,
        EXTRACT(ISODOW FROM purchased_at)::integer AS first_order_purchase_weekday,
        EXTRACT(EPOCH FROM (approved_at - purchased_at)) / 3600.0
            AS first_order_approval_hours,
        EXTRACT(EPOCH FROM (delivered_to_carrier_at - approved_at)) / 3600.0
            AS first_order_carrier_handoff_hours
    FROM delivered_orders
    ORDER BY customer_key, delivered_at, order_id
),
first_order_item_features AS (
    SELECT
        first_orders.customer_key,
        MAX(items.price) AS first_order_max_item_revenue,
        AVG(items.price) AS first_order_average_item_revenue,
        COUNT(DISTINCT sellers.seller_state) AS first_order_seller_state_count,
        BOOL_OR(sellers.seller_state <> first_orders.customer_state)
            AS first_order_cross_state
    FROM first_delivered_orders AS first_orders
    JOIN warehouse.fact_order_items AS items
        ON first_orders.order_id = items.order_id
    JOIN warehouse.dim_seller AS sellers
        ON items.seller_key = sellers.seller_key
    GROUP BY first_orders.customer_key
),
first_order_categories AS (
    SELECT
        first_orders.customer_key,
        COUNT(DISTINCT COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
        )) AS first_order_distinct_category_count,
        (
            ARRAY_AGG(
                COALESCE(
                    products.category_name_english,
                    products.category_name_pt,
                    'unknown'
                )
                ORDER BY items.price DESC,
                    COALESCE(
                        products.category_name_english,
                        products.category_name_pt,
                        'unknown'
                    ) ASC
            )
        )[1] AS first_order_primary_category
    FROM first_delivered_orders AS first_orders
    JOIN warehouse.fact_order_items AS items
        ON first_orders.order_id = items.order_id
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
    GROUP BY first_orders.customer_key
),
first_order_payments AS (
    SELECT
        first_orders.customer_key,
        COUNT(DISTINCT payments.payment_type) AS first_order_payment_type_count,
        MAX(payments.payment_installments) AS first_order_max_installments
    FROM first_delivered_orders AS first_orders
    JOIN warehouse.fact_payments AS payments
        ON first_orders.order_id = payments.order_id
    GROUP BY first_orders.customer_key
),
data_end AS (
    SELECT MAX(delivered_at) AS observed_through
    FROM delivered_orders
),
labels AS (
    SELECT
        first_orders.customer_key,
        BOOL_OR(
            later_orders.purchased_at > first_orders.prediction_time
            AND later_orders.purchased_at
                <= first_orders.prediction_time + INTERVAL '90 days'
        ) AS repurchased_within_90d
    FROM first_delivered_orders AS first_orders
    LEFT JOIN delivered_orders AS later_orders
        ON first_orders.customer_key = later_orders.customer_key
    GROUP BY first_orders.customer_key
)
SELECT
    first_orders.customer_key,
    first_orders.prediction_time,
    first_orders.prediction_time AS feature_available_at,
    first_orders.first_order_purchased_at,
    first_orders.first_order_item_count,
    first_orders.first_order_item_revenue,
    first_orders.first_order_freight_revenue,
    first_orders.first_order_payment_value,
    first_orders.first_order_delivery_days,
    first_orders.customer_state,
    categories.first_order_primary_category,
    item_features.first_order_max_item_revenue,
    item_features.first_order_average_item_revenue,
    first_orders.first_order_freight_revenue
        / NULLIF(first_orders.first_order_item_revenue, 0)
        AS first_order_freight_rate,
    payments.first_order_payment_type_count,
    payments.first_order_max_installments,
    item_features.first_order_seller_state_count,
    item_features.first_order_cross_state,
    first_orders.first_order_estimated_delivery_days,
    first_orders.first_order_delivery_vs_estimate_days,
    first_orders.first_order_is_late,
    first_orders.first_order_purchase_month,
    first_orders.first_order_purchase_weekday,
    first_orders.first_order_approval_hours,
    first_orders.first_order_carrier_handoff_hours,
    categories.first_order_distinct_category_count,
    data_end.observed_through,
    data_end.observed_through >= first_orders.prediction_time + INTERVAL '90 days'
        AS eligible_for_90d,
    CASE
        WHEN data_end.observed_through
            < first_orders.prediction_time + INTERVAL '90 days' THEN NULL
        ELSE labels.repurchased_within_90d
    END AS repurchased_within_90d
FROM first_delivered_orders AS first_orders
CROSS JOIN data_end
JOIN labels
    ON first_orders.customer_key = labels.customer_key
LEFT JOIN first_order_categories AS categories
    ON first_orders.customer_key = categories.customer_key
LEFT JOIN first_order_item_features AS item_features
    ON first_orders.customer_key = item_features.customer_key
LEFT JOIN first_order_payments AS payments
    ON first_orders.customer_key = payments.customer_key;

ALTER TABLE marts.ml_customer_features
ADD CONSTRAINT ml_customer_features_pkey PRIMARY KEY (customer_key);
