CREATE TABLE warehouse.fact_orders AS
WITH item_by_order AS (
    SELECT
        order_id,
        COUNT(*) AS item_count,
        SUM(price) AS item_revenue,
        SUM(freight_value) AS freight_revenue
    FROM staging.order_items
    GROUP BY order_id
),
payment_by_order AS (
    SELECT
        order_id,
        COUNT(*) AS payment_count,
        SUM(payment_value) AS payment_value
    FROM staging.payments
    GROUP BY order_id
)
SELECT
    orders.order_id,
    customers.customer_key,
    dates.date_key AS purchase_date_key,
    orders.customer_id AS source_customer_id,
    source_customers.customer_state,
    orders.order_status,
    orders.purchased_at,
    orders.approved_at,
    orders.delivered_to_carrier_at,
    orders.delivered_at,
    orders.estimated_delivery_at,
    orders.is_delivery_late,
    orders.has_delivery_timestamp_anomaly,
    orders.has_status_timestamp_anomaly,
    COALESCE(items.item_count, 0) AS item_count,
    COALESCE(items.item_revenue, 0::numeric) AS item_revenue,
    COALESCE(items.freight_revenue, 0::numeric) AS freight_revenue,
    COALESCE(payments.payment_count, 0) AS payment_count,
    COALESCE(payments.payment_value, 0::numeric) AS payment_value
FROM staging.orders AS orders
JOIN raw.customers AS source_customers
    ON orders.customer_id = source_customers.customer_id
JOIN warehouse.dim_customer AS customers
    ON source_customers.customer_unique_id = customers.customer_unique_id
JOIN warehouse.dim_date AS dates
    ON orders.purchased_at::date = dates.date_value
LEFT JOIN item_by_order AS items
    ON orders.order_id = items.order_id
LEFT JOIN payment_by_order AS payments
    ON orders.order_id = payments.order_id;

ALTER TABLE warehouse.fact_orders
ADD CONSTRAINT fact_orders_pkey PRIMARY KEY (order_id);

ALTER TABLE warehouse.fact_orders
ADD CONSTRAINT fact_orders_customer_key_fkey
FOREIGN KEY (customer_key)
REFERENCES warehouse.dim_customer (customer_key);

ALTER TABLE warehouse.fact_orders
ADD CONSTRAINT fact_orders_purchase_date_key_fkey
FOREIGN KEY (purchase_date_key)
REFERENCES warehouse.dim_date (date_key);

CREATE TABLE warehouse.fact_order_items AS
SELECT
    items.order_id,
    items.order_item_id,
    items.product_id,
    items.seller_id,
    products.product_key,
    sellers.seller_key,
    items.shipping_limit_at,
    items.price,
    items.freight_value
FROM staging.order_items AS items
JOIN warehouse.dim_product AS products
    ON items.product_id = products.product_id
JOIN warehouse.dim_seller AS sellers
    ON items.seller_id = sellers.seller_id;

ALTER TABLE warehouse.fact_order_items
ADD CONSTRAINT fact_order_items_pkey PRIMARY KEY (order_id, order_item_id);

ALTER TABLE warehouse.fact_order_items
ADD CONSTRAINT fact_order_items_order_fkey
FOREIGN KEY (order_id)
REFERENCES warehouse.fact_orders (order_id);

ALTER TABLE warehouse.fact_order_items
ADD CONSTRAINT fact_order_items_product_key_fkey
FOREIGN KEY (product_key)
REFERENCES warehouse.dim_product (product_key);

ALTER TABLE warehouse.fact_order_items
ADD CONSTRAINT fact_order_items_seller_key_fkey
FOREIGN KEY (seller_key)
REFERENCES warehouse.dim_seller (seller_key);

CREATE TABLE warehouse.fact_payments AS
SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
FROM staging.payments;

ALTER TABLE warehouse.fact_payments
ADD CONSTRAINT fact_payments_pkey PRIMARY KEY (order_id, payment_sequential);

ALTER TABLE warehouse.fact_payments
ADD CONSTRAINT fact_payments_order_fkey
FOREIGN KEY (order_id)
REFERENCES warehouse.fact_orders (order_id);

CREATE TABLE warehouse.fact_reviews AS
SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_created_at,
    review_answered_at
FROM staging.reviews;

ALTER TABLE warehouse.fact_reviews
ADD CONSTRAINT fact_reviews_pkey PRIMARY KEY (review_id, order_id);

ALTER TABLE warehouse.fact_reviews
ADD CONSTRAINT fact_reviews_order_fkey
FOREIGN KEY (order_id)
REFERENCES warehouse.fact_orders (order_id);
