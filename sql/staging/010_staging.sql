CREATE TABLE staging.orders AS
WITH typed_orders AS (
    SELECT
        order_id,
        customer_id,
        LOWER(TRIM(order_status)) AS order_status,
        NULLIF(order_purchase_timestamp, '')::timestamp AS purchased_at,
        NULLIF(order_approved_at, '')::timestamp AS approved_at,
        NULLIF(order_delivered_carrier_date, '')::timestamp
            AS delivered_to_carrier_at,
        NULLIF(order_delivered_customer_date, '')::timestamp AS delivered_at,
        NULLIF(order_estimated_delivery_date, '')::timestamp
            AS estimated_delivery_at
    FROM raw.orders
)
SELECT
    *,
    CASE
        WHEN order_status <> 'delivered' THEN NULL
        WHEN delivered_at IS NULL OR estimated_delivery_at IS NULL THEN NULL
        ELSE delivered_at > estimated_delivery_at
    END AS is_delivery_late,
    (order_status = 'delivered' AND delivered_at IS NULL)
        AS has_delivery_timestamp_anomaly,
    (order_status <> 'delivered' AND delivered_at IS NOT NULL)
        AS has_status_timestamp_anomaly
FROM typed_orders;

ALTER TABLE staging.orders
ADD CONSTRAINT staging_orders_pkey PRIMARY KEY (order_id);

CREATE TABLE staging.order_items AS
SELECT
    order_id,
    order_item_id::integer AS order_item_id,
    product_id,
    seller_id,
    NULLIF(shipping_limit_date, '')::timestamp AS shipping_limit_at,
    NULLIF(price, '')::numeric(12, 2) AS price,
    NULLIF(freight_value, '')::numeric(12, 2) AS freight_value
FROM raw.order_items;

ALTER TABLE staging.order_items
ADD CONSTRAINT staging_order_items_pkey PRIMARY KEY (order_id, order_item_id);

CREATE TABLE staging.payments AS
SELECT
    order_id,
    payment_sequential::integer AS payment_sequential,
    payment_type,
    payment_installments::integer AS payment_installments,
    NULLIF(payment_value, '')::numeric(12, 2) AS payment_value
FROM raw.payments;

ALTER TABLE staging.payments
ADD CONSTRAINT staging_payments_pkey PRIMARY KEY (order_id, payment_sequential);

CREATE TABLE staging.products AS
SELECT
    products.product_id,
    NULLIF(TRIM(products.product_category_name), '') AS category_name_pt,
    NULLIF(TRIM(translation.product_category_name_english), '')
        AS category_name_english,
    NULLIF(products.product_name_lenght, '')::integer AS product_name_length,
    NULLIF(products.product_description_lenght, '')::integer
        AS product_description_length,
    NULLIF(products.product_photos_qty, '')::integer AS product_photos_qty,
    NULLIF(products.product_weight_g, '')::numeric AS product_weight_g,
    NULLIF(products.product_length_cm, '')::numeric AS product_length_cm,
    NULLIF(products.product_height_cm, '')::numeric AS product_height_cm,
    NULLIF(products.product_width_cm, '')::numeric AS product_width_cm,
    products.product_category_name IS NULL AS has_missing_category,
    (
        products.product_category_name IS NOT NULL
        AND translation.product_category_name_english IS NULL
    ) AS has_missing_translation
FROM raw.products AS products
LEFT JOIN raw.category_translation AS translation
    ON products.product_category_name = translation.product_category_name;

ALTER TABLE staging.products
ADD CONSTRAINT staging_products_pkey PRIMARY KEY (product_id);

CREATE TABLE staging.sellers AS
SELECT
    seller_id,
    LPAD(NULLIF(TRIM(seller_zip_code_prefix), ''), 5, '0')
        AS seller_zip_code_prefix,
    LOWER(TRIM(seller_city)) AS seller_city,
    UPPER(TRIM(seller_state)) AS seller_state
FROM raw.sellers;

ALTER TABLE staging.sellers
ADD CONSTRAINT staging_sellers_pkey PRIMARY KEY (seller_id);

CREATE TABLE staging.reviews AS
SELECT
    review_id,
    order_id,
    NULLIF(review_score, '')::integer AS review_score,
    NULLIF(review_comment_title, '') AS review_comment_title,
    NULLIF(review_comment_message, '') AS review_comment_message,
    NULLIF(review_creation_date, '')::timestamp AS review_created_at,
    NULLIF(review_answer_timestamp, '')::timestamp AS review_answered_at
FROM raw.reviews;

ALTER TABLE staging.reviews
ADD CONSTRAINT staging_reviews_pkey PRIMARY KEY (review_id, order_id);
