CREATE TABLE marts.repurchase_horizons AS
WITH delivered_orders AS (
    SELECT customer_key, purchased_at
    FROM warehouse.fact_orders
    WHERE order_status = 'delivered'
),
data_end AS (
    SELECT MAX(purchased_at) AS as_of_timestamp
    FROM delivered_orders
),
first_purchase AS (
    SELECT customer_key, MIN(purchased_at) AS first_purchase_at
    FROM delivered_orders
    GROUP BY customer_key
),
horizons AS (
    SELECT horizon_days
    FROM (VALUES (30), (60), (90)) AS values_table(horizon_days)
),
next_purchase AS (
    SELECT
        first_purchase.customer_key,
        MIN(later_orders.purchased_at) FILTER (
            WHERE later_orders.purchased_at > first_purchase.first_purchase_at
        ) AS next_purchase_at
    FROM first_purchase
    JOIN delivered_orders AS later_orders
        ON first_purchase.customer_key = later_orders.customer_key
    GROUP BY first_purchase.customer_key
),
customer_horizons AS (
    SELECT
        first_purchase.customer_key,
        horizons.horizon_days,
        data_end.as_of_timestamp::date >= first_purchase.first_purchase_at::date
            + horizons.horizon_days * INTERVAL '1 day' AS is_eligible,
        next_purchase.next_purchase_at <= first_purchase.first_purchase_at
            + horizons.horizon_days * INTERVAL '1 day'
            AS repurchased_within_horizon
    FROM first_purchase
    JOIN next_purchase
        ON first_purchase.customer_key = next_purchase.customer_key
    CROSS JOIN horizons
    CROSS JOIN data_end
),
aggregated AS (
    SELECT
        horizon_days,
        COUNT(*) FILTER (WHERE is_eligible) AS eligible_customers,
        COUNT(*) FILTER (
            WHERE is_eligible AND repurchased_within_horizon
        ) AS repurchased_customers
    FROM customer_horizons
    GROUP BY horizon_days
),
rates AS (
    SELECT
        horizon_days,
        eligible_customers,
        repurchased_customers,
        repurchased_customers::numeric / eligible_customers AS repurchase_rate
    FROM aggregated
)
SELECT
    horizon_days,
    eligible_customers,
    repurchased_customers,
    ROUND(repurchase_rate * 100, 3) AS repurchase_rate_pct,
    ROUND(
        (
            (
                repurchase_rate + 1.96 * 1.96 / (2 * eligible_customers)
            ) / (1 + 1.96 * 1.96 / eligible_customers)
            - 1.96 * SQRT(
                repurchase_rate * (1 - repurchase_rate) / eligible_customers
                + 1.96 * 1.96 / (4 * eligible_customers * eligible_customers)
            ) / (1 + 1.96 * 1.96 / eligible_customers)
        ) * 100,
        3
    ) AS ci_lower_pct,
    ROUND(
        (
            (
                repurchase_rate + 1.96 * 1.96 / (2 * eligible_customers)
            ) / (1 + 1.96 * 1.96 / eligible_customers)
            + 1.96 * SQRT(
                repurchase_rate * (1 - repurchase_rate) / eligible_customers
                + 1.96 * 1.96 / (4 * eligible_customers * eligible_customers)
            ) / (1 + 1.96 * 1.96 / eligible_customers)
        ) * 100,
        3
    ) AS ci_upper_pct
FROM rates;

ALTER TABLE marts.repurchase_horizons
ADD CONSTRAINT repurchase_horizons_pkey PRIMARY KEY (horizon_days);
