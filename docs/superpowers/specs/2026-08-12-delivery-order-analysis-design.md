# Delivery Order Analysis Design

## Purpose

Create an order-grain mart for testing whether late and on-time delivered orders have different review-score distributions, while preserving the project's governed 90-day repurchase-label definition.

## Data contract

`marts.delivery_order_analysis` has exactly one row per delivered `order_id` and contains `order_id`, `customer_key`, `delivery_status`, `delivery_days`, `delivery_vs_estimate_days`, `review_score`, `is_first_delivered_order`, `eligible_for_90d`, and `repurchased_within_90d`.

`delivery_status` is `late` when `warehouse.fact_orders.is_delivery_late` is true; otherwise it is `on_time`. Review scores are aggregated to one value per order before joining. The eligibility and label fields are populated only for first delivered orders, so their denominator remains consistent with the governed repurchase definition.

## Statistical analysis

For orders with non-null review scores, map `on_time` to group 0 and `late` to group 1. Run the existing two-sided Mann-Whitney U comparison and report group sizes, medians, median difference, deterministic bootstrap 95% interval, p-value, and rank-biserial correlation. The result is observational and must explicitly exclude causal interpretation because category, seller, geography, order time, and other confounders are uncontrolled.

## Verification

The mart rebuild script drops and recreates the table. Tests prove its delivered-order grain, mutually exclusive delivery statuses, and first-order-only label behavior. A script runs the real rating comparison and writes its auditable result into the findings document.
