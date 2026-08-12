# Delivery Order Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an order-grain delivery mart and produce an auditable Mann-Whitney U review-score comparison.

**Architecture:** SQL creates one row per delivered order, aggregating reviews before joining them to orders. A small Python script queries the mart and passes its review-score arrays to `compare_binary_groups`, producing a markdown finding based on the governed statistical result.

**Tech Stack:** PostgreSQL 16, SQLAlchemy, Pandas, NumPy, SciPy, pytest.

## Global Constraints

- Only delivered orders are analysed.
- Never directly join item and payment detail for financial measures.
- The 90-day label is populated only for first delivered orders with a complete observation window.
- The statistical conclusion is associational, not causal.
- Use deterministic bootstrap intervals and test before implementation.

---

### Task 1: Order-grain delivery mart

**Files:**
- Create: `sql/marts/035_delivery_order_analysis.sql`
- Modify: `scripts/build_marts.py`
- Modify: `tests/sql/test_product_delivery_marts.py`

- [ ] **Step 1: Add a mart invariant test**

Assert that the rebuilt table has one row per delivered order, only `on_time`/`late` statuses, and non-null repurchase labels only where `is_first_delivered_order` and `eligible_for_90d` are true.

- [ ] **Step 2: Run the test and observe the missing-mart failure**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py -v --basetemp .pytest-tmp\\delivery-order-red`

- [ ] **Step 3: Implement the mart and rebuild hook**

Aggregate `fact_reviews` by `order_id`, select delivered orders, derive delivery status and duration fields, identify each customer's first delivered order, and left join `marts.customer_360` for the governed label fields.

- [ ] **Step 4: Verify the SQL mart**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py -v --basetemp .pytest-tmp\\delivery-order-green`

### Task 2: Review-score statistical finding

**Files:**
- Create: `scripts/analyze_delivery_reviews.py`
- Create: `docs/analysis/findings.md`
- Modify: `docs/learning/week-2.md`
- Test: `tests/analytics/test_statistics.py`

- [ ] **Step 1: Implement the analysis script**

Query non-null review scores from `marts.delivery_order_analysis`, map `on_time` to 0 and `late` to 1, call `compare_binary_groups`, and print all returned fields as JSON-compatible values.

- [ ] **Step 2: Run the script after mart rebuild**

Run: `python scripts/build_marts.py; python scripts/analyze_delivery_reviews.py`

- [ ] **Step 3: Write the finding**

Record the exact result under “现象—证据—限制—行动建议”, state that the test is two-sided Mann-Whitney U, and state that the result is associative only.

- [ ] **Step 4: Run full verification**

Run: `python -m pytest -v --basetemp .pytest-tmp\\delivery-analysis-full; python -m ruff check src tests scripts`
