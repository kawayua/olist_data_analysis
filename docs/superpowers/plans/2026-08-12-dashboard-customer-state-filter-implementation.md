# Dashboard Customer-State Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a customer-state performance mart and parameterized repository interfaces for a real Dashboard state filter.

**Architecture:** PostgreSQL derives customer state from each order's source customer address and creates one state-level record. The read-only repository uses bound SQL parameters to return the state list and state performance, while existing all-state marts remain unchanged.

**Tech Stack:** PostgreSQL 16, SQLAlchemy, Pandas, pytest.

## Global Constraints

- Customer state means the receiving-address state from `raw.customers.customer_state`.
- Only delivered orders are included.
- 90-day labels use only first delivered orders with complete observation windows.
- User values are always passed through SQLAlchemy parameters.
- Existing global marts must retain their current grain and results.

---

### Task 1: State performance mart

**Files:**
- Create: `sql/marts/036_state_performance.sql`
- Modify: `scripts/build_marts.py`
- Modify: `tests/sql/test_product_delivery_marts.py`

- [ ] **Step 1: Write the failing mart invariant test**

Add an assertion that `marts.state_performance` is rebuilt, has one row per `customer_state`, includes rows, and has only rate values from 0 to 100.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py -v --basetemp .pytest-tmp\\state-mart-red`

- [ ] **Step 3: Implement the state mart**

Use `warehouse.fact_orders.source_customer_id = raw.customers.customer_id`, keep delivered orders, aggregate by `customer_state`, and calculate revenue, AOV, late rate, eligible first-purchase customers, repurchased first-purchase customers, and the governed 90-day rate.

- [ ] **Step 4: Rebuild and verify**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py -v --basetemp .pytest-tmp\\state-mart-green`

### Task 2: Parameterized state repository interface

**Files:**
- Modify: `src/analytics/repository.py`
- Modify: `tests/analytics/test_repository.py`

- [ ] **Step 1: Write repository tests**

Assert `available_customer_states()` queries the state mart and `state_performance(AnalyticsFilters(customer_state="SP"))` binds `{"customer_state": "SP"}` rather than embedding its value in SQL.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/analytics/test_repository.py -v --basetemp .pytest-tmp\\state-repository-red`

- [ ] **Step 3: Implement filters and repository methods**

Add `customer_state` to `AnalyticsFilters`, implement `available_customer_states()` and `state_performance(filters)`, and pass all state values as query parameters.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/analytics/test_repository.py -v --basetemp .pytest-tmp\\state-repository-green`

- [ ] **Step 5: Run verification**

Run: `python -m pytest -v --basetemp .pytest-tmp\\state-filter-full; python -m ruff check src tests scripts`
