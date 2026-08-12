CREATE TABLE marts.cohort_retention AS
WITH customer_orders AS (
    SELECT DISTINCT
        customer_key,
        DATE_TRUNC('month', purchased_at)::date AS purchase_month
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
first_purchase AS (
    SELECT
        customer_key,
        MIN(purchase_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_key
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customers
    FROM first_purchase
    GROUP BY cohort_month
),
cohort_activity AS (
    SELECT
        first_purchase.cohort_month,
        customer_orders.purchase_month AS activity_month,
        COUNT(DISTINCT first_purchase.customer_key) AS retained_customers
    FROM first_purchase
    JOIN customer_orders
        ON first_purchase.customer_key = customer_orders.customer_key
    GROUP BY
        first_purchase.cohort_month,
        customer_orders.purchase_month
),
data_bounds AS (
    SELECT
        MIN(purchase_month) AS data_start_month,
        MAX(purchase_month) AS data_end_month
    FROM customer_orders
),
cohort_calendar AS (
    SELECT
        sizes.cohort_month,
        sizes.cohort_customers,
        months.activity_month::date AS activity_month,
        bounds.data_start_month,
        bounds.data_end_month
    FROM cohort_sizes AS sizes
    CROSS JOIN data_bounds AS bounds
    CROSS JOIN LATERAL generate_series(
        sizes.cohort_month::timestamp,
        bounds.data_end_month::timestamp,
        INTERVAL '1 month'
    ) AS months(activity_month)
)
SELECT
    calendar.cohort_month,
    calendar.activity_month,
    (
        EXTRACT(YEAR FROM calendar.activity_month)::integer
        - EXTRACT(YEAR FROM calendar.cohort_month)::integer
    ) * 12
    + EXTRACT(MONTH FROM calendar.activity_month)::integer
    - EXTRACT(MONTH FROM calendar.cohort_month)::integer
        AS months_since_cohort,
    calendar.cohort_customers,
    COALESCE(activity.retained_customers, 0) AS retained_customers,
    ROUND(
        COALESCE(activity.retained_customers, 0)::numeric
        / calendar.cohort_customers * 100,
        3
    ) AS retention_rate_pct,
    calendar.activity_month > calendar.data_start_month
        AND calendar.activity_month < calendar.data_end_month
        AS is_complete_observation_month
FROM cohort_calendar AS calendar
LEFT JOIN cohort_activity AS activity
    ON calendar.cohort_month = activity.cohort_month
    AND calendar.activity_month = activity.activity_month;

ALTER TABLE marts.cohort_retention
ADD CONSTRAINT cohort_retention_pkey PRIMARY KEY (cohort_month, activity_month);
