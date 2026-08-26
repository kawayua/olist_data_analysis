CREATE TABLE marts.state_product_performance AS
WITH delivered_order_items AS (
    SELECT
        customers.customer_state,
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
    JOIN raw.customers AS customers
        ON orders.source_customer_id = customers.customer_id
    JOIN warehouse.fact_order_items AS items
        ON orders.order_id = items.order_id
    JOIN warehouse.dim_product AS products
        ON items.product_key = products.product_key
    WHERE orders.order_status = 'delivered'
      AND customers.customer_state IS NOT NULL
)
SELECT
    customer_state,
    product_category,
    COUNT(DISTINCT order_id) AS order_count,
    COUNT(DISTINCT customer_key) AS customer_count,
    SUM(item_revenue) AS item_revenue,
    SUM(freight_revenue) AS freight_revenue,
    ROUND(
        SUM(item_revenue) / NULLIF(COUNT(DISTINCT order_id), 0),
        2
    ) AS item_revenue_aov
FROM delivered_order_items
GROUP BY customer_state, product_category;

ALTER TABLE marts.state_product_performance
ADD CONSTRAINT state_product_performance_pkey
PRIMARY KEY (customer_state, product_category);
