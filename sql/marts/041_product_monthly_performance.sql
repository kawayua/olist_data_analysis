CREATE TABLE marts.product_monthly_performance AS
WITH delivered_order_items AS (
    SELECT
        DATE_TRUNC('month', orders.purchased_at)::date AS month_start,
        COALESCE(
            products.category_name_english,
            products.category_name_pt,
            'unknown'
        ) AS product_category,
        orders.order_id,
        orders.customer_key,
        items.price AS item_revenue,
        items.freight_value AS freight_revenue
    FROM warehouse.fact_orders AS orders
    JOIN warehouse.fact_order_items AS items
        ON orders.order_id = items.order_id
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
    WHERE orders.order_status = 'delivered'
),
data_bounds AS (
    SELECT
        MIN(month_start) AS first_month,
        MAX(month_start) AS last_month
    FROM delivered_order_items
)
SELECT
    items.month_start,
    items.product_category,
    COUNT(DISTINCT items.order_id) AS order_count,
    COUNT(DISTINCT items.customer_key) AS customer_count,
    SUM(items.item_revenue) AS item_revenue,
    SUM(items.freight_revenue) AS freight_revenue,
    ROUND(
        SUM(items.item_revenue) / NULLIF(COUNT(DISTINCT items.order_id), 0),
        2
    ) AS item_revenue_aov,
    items.month_start > bounds.first_month
        AND items.month_start < bounds.last_month AS is_complete_month
FROM delivered_order_items AS items
CROSS JOIN data_bounds AS bounds
GROUP BY items.month_start, items.product_category, bounds.first_month, bounds.last_month;

ALTER TABLE marts.product_monthly_performance
ADD CONSTRAINT product_monthly_performance_pkey
PRIMARY KEY (month_start, product_category);
