# Dashboard Customer-State Filter Design

## Purpose

Add a real Dashboard state filter based on the customer's receiving address, so market performance is interpreted by customer location rather than seller location.

## Data contract

`marts.state_performance` has one row per `customer_state`. It includes delivered-order count, distinct customer count, item revenue, payment value, item-revenue AOV, delayed-delivery rate, eligible first-purchase customer count, repurchased first-purchase customer count, and 90-day repurchase rate.

The customer state comes from `raw.customers.customer_state` by joining `warehouse.fact_orders.source_customer_id` to the source customer identifier. This preserves the customer identity used in `warehouse.dim_customer` while retaining the order-specific delivery-address state.

## Dashboard filter scope

`AnalyticsFilters.customer_state` is a bound parameter. The repository exposes `available_customer_states()` and `state_performance(filters)`. State filtering is initially applied to state performance only. Global monthly, cohort, segment, product, and delivery marts retain their current all-state grain until state-filtered variants are separately designed, preventing silently ineffective filters.

## Verification

The mart has exactly one row per non-null customer state, valid rates in [0, 100], and a customer-state primary key. Repository tests verify state is passed through SQLAlchemy parameters rather than string concatenation.
