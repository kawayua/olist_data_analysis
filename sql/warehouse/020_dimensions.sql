CREATE TABLE warehouse.dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_unique_id TEXT NOT NULL UNIQUE
);

INSERT INTO warehouse.dim_customer (customer_unique_id)
SELECT DISTINCT customer_unique_id
FROM raw.customers
ORDER BY customer_unique_id;

CREATE TABLE warehouse.dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id TEXT NOT NULL UNIQUE,
    category_name_pt TEXT,
    category_name_english TEXT,
    product_name_length INTEGER,
    product_description_length INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC,
    product_length_cm NUMERIC,
    product_height_cm NUMERIC,
    product_width_cm NUMERIC,
    has_missing_category BOOLEAN NOT NULL,
    has_missing_translation BOOLEAN NOT NULL
);

INSERT INTO warehouse.dim_product (
    product_id,
    category_name_pt,
    category_name_english,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    has_missing_category,
    has_missing_translation
)
SELECT
    product_id,
    category_name_pt,
    category_name_english,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    has_missing_category,
    has_missing_translation
FROM staging.products;

CREATE TABLE warehouse.dim_seller (
    seller_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id TEXT NOT NULL UNIQUE,
    seller_zip_code_prefix TEXT NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state TEXT NOT NULL
);

INSERT INTO warehouse.dim_seller (
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
)
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM staging.sellers;

CREATE TABLE warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    date_value DATE NOT NULL UNIQUE,
    calendar_year SMALLINT NOT NULL,
    calendar_quarter SMALLINT NOT NULL,
    calendar_month SMALLINT NOT NULL,
    year_month TEXT NOT NULL,
    month_name TEXT NOT NULL,
    iso_week SMALLINT NOT NULL,
    iso_day_of_week SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

WITH date_bounds AS (
    SELECT
        MIN(purchased_at)::date AS first_date,
        MAX(purchased_at)::date AS last_date
    FROM staging.orders
    WHERE purchased_at IS NOT NULL
)
INSERT INTO warehouse.dim_date (
    date_key,
    date_value,
    calendar_year,
    calendar_quarter,
    calendar_month,
    year_month,
    month_name,
    iso_week,
    iso_day_of_week,
    is_weekend
)
SELECT
    TO_CHAR(days.date_value, 'YYYYMMDD')::integer,
    days.date_value,
    EXTRACT(YEAR FROM days.date_value)::smallint,
    EXTRACT(QUARTER FROM days.date_value)::smallint,
    EXTRACT(MONTH FROM days.date_value)::smallint,
    TO_CHAR(days.date_value, 'YYYY-MM'),
    TO_CHAR(days.date_value, 'FMMonth'),
    EXTRACT(WEEK FROM days.date_value)::smallint,
    EXTRACT(ISODOW FROM days.date_value)::smallint,
    EXTRACT(ISODOW FROM days.date_value) IN (6, 7)
FROM date_bounds
CROSS JOIN LATERAL generate_series(
    date_bounds.first_date,
    date_bounds.last_date,
    INTERVAL '1 day'
) AS days(date_value);
