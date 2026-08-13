CREATE TABLE marts.product_performance AS
WITH delivered_orders AS (
    SELECT
        order_id,
        customer_key,
        item_revenue,
        freight_revenue,
        is_delivery_late
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
order_categories AS (
    SELECT
        items.order_id,
        COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
        ) AS product_category,
        SUM(items.price) AS category_item_revenue,
        SUM(items.freight_value) AS category_freight_revenue
    FROM warehouse.fact_order_items AS items
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
    GROUP BY
        items.order_id,
        COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
    )
),
customer_first_orders AS (
    SELECT DISTINCT ON (customer_key)
        customer_key,
        order_id
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
    ORDER BY customer_key, purchased_at, order_id
),
order_reviews AS (
    SELECT order_id, AVG(review_score) AS average_review_score
    FROM warehouse.fact_reviews
    GROUP BY order_id
)
SELECT
    categories.product_category,
    COUNT(DISTINCT orders.order_id) AS order_count,
    COUNT(DISTINCT orders.customer_key) AS customer_count,
    SUM(categories.category_item_revenue) AS item_revenue,
    SUM(categories.category_freight_revenue) AS freight_revenue,
    ROUND(
        SUM(categories.category_freight_revenue)
        / NULLIF(SUM(categories.category_item_revenue), 0) * 100,
        3
    ) AS freight_rate_pct,
    ROUND(AVG(orders.is_delivery_late::integer) * 100, 3) AS delayed_delivery_rate_pct,
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
JOIN order_categories AS categories
    ON orders.order_id = categories.order_id
JOIN customer_first_orders AS first_orders
    ON orders.customer_key = first_orders.customer_key
JOIN marts.customer_360 AS customer_360
    ON orders.customer_key = customer_360.customer_key
LEFT JOIN order_reviews AS reviews
    ON orders.order_id = reviews.order_id
GROUP BY categories.product_category;

ALTER TABLE marts.product_performance
ADD CONSTRAINT product_performance_pkey PRIMARY KEY (product_category);
