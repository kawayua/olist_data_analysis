# Olist Dashboard Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the five-page Olist business Dashboard from the user-provided design document, with governed data and page-scoped filters.

**Architecture:** Add only the marts necessary for missing analytical questions. Keep Streamlit pages behind `AnalyticsRepository`, parameterized queries, reusable Plotly factories, and page-local filter components.

**Tech Stack:** PostgreSQL, SQLAlchemy, pandas, Plotly, Streamlit, pytest, Ruff.

## Global Constraints

- Only delivered orders contribute to commerce, delivery, and repurchase metrics.
- State means the customer receiving state.
- Pages must use `AnalyticsRepository`; no page creates a database connection or SQL string.
- A filter appears only where the associated mart truly applies it.
- Aggregated rates are denominator-weighted, never summed.
- Delivery/rating evidence is labelled association rather than causation.

---

### Task 1: Page-scoped filters and correct state aggregation

**Files:**
- Modify: `app/components/filters.py`, `app/components/presentation.py`, `app/Home.py`
- Modify: `app/pages/1_经营总览.py` through `app/pages/5_商品与履约.py`
- Modify: `tests/visualization/test_dashboard_components.py`, `tests/visualization/test_dashboard_pages.py`

**Interfaces:**
- Produces: `render_state_filter`, `render_month_filter`, `render_cohort_filter`, `render_category_filter`, and `summarize_state_performance(frame) -> pd.Series`.

- [ ] **Step 1: Write failing component tests**

```python
def test_state_summary_weights_rates_by_their_denominators():
    frame = pd.DataFrame({
        "order_count": [100, 1],
        "delayed_delivery_rate_pct": [10.0, 100.0],
        "eligible_first_purchase_customers": [100, 1],
        "repurchased_first_purchase_customers": [20, 1],
    })
    summary = summarize_state_performance(frame)
    assert summary.delayed_delivery_rate_pct == pytest.approx(10.891, abs=0.001)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/visualization/test_dashboard_components.py -v --basetemp .pytest-tmp\page-filters-red`

Expected: FAIL because the summary and page-specific controls do not exist.

- [ ] **Step 3: Implement only effective controls**

Use state on P1; month range and incomplete-month switch on P2; cohort month and incomplete-observation switch on P3; category on P5; no filter on Home or P4 customer value. Place controls between header and KPIs, with a scope caption. Make `summary` calculate delay numerator from orders and repeat denominator from eligible first-purchase customers.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/visualization/test_dashboard_components.py tests/visualization/test_dashboard_pages.py -v --basetemp .pytest-tmp\page-filters-green`

Run: `python -m ruff check app tests/visualization`

Commit: `git add app tests/visualization && git commit -m "feat: scope dashboard filters by page"`

### Task 2: Monthly operating and growth-driver measures

**Files:**
- Modify: `sql/marts/030_monthly_growth.sql`, `scripts/build_marts.py`
- Modify: `tests/sql/test_monthly_growth.py`, `src/analytics/repository.py`, `tests/analytics/test_repository.py`

**Interfaces:**
- Produces: monthly active buyers, orders, revenue, AOV, average review score, new/returning revenue, and MoM rates for buyers, orders, revenue, and AOV.

- [ ] **Step 1: Write a missing-column test**

```python
def test_monthly_growth_has_growth_driver_metrics():
    columns = connection.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'marts' AND table_name = 'monthly_growth'
    """)).scalars().all()
    expected = {"active_customers_mom_pct", "order_count_mom_pct", "item_revenue_aov_mom_pct", "average_review_score"}
    assert expected <= set(columns)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/sql/test_monthly_growth.py -v --basetemp .pytest-tmp\monthly-drivers-red`

Expected: FAIL because the driver columns are absent.

- [ ] **Step 3: Implement rate-safe monthly measures**

Extend `marts.monthly_growth`. Calculate AOV before using its `LAG`, use `NULL` for zero prior denominators, and aggregate one order-level average review score per month. Keep the existing date parameter binding unchanged.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/sql/test_monthly_growth.py tests/analytics/test_repository.py -v --basetemp .pytest-tmp\monthly-drivers-green`

Commit: `git add sql/marts/030_monthly_growth.sql scripts/build_marts.py tests/sql/test_monthly_growth.py src/analytics/repository.py tests/analytics/test_repository.py && git commit -m "feat: add monthly growth drivers"`

### Task 3: Customer value and repurchase-behavior marts

**Files:**
- Create: `sql/marts/037_customer_value_analysis.sql`, `sql/marts/038_repurchase_behavior.sql`
- Modify: `scripts/build_marts.py`, `src/analytics/repository.py`, `tests/analytics/test_repository.py`
- Create: `tests/sql/test_customer_value_repurchases.py`

**Interfaces:**
- Produces: `customer_value_analysis` at customer-segment grain; `repurchase_behavior` for 30/60/90-day category repeat rates and next-purchase interval buckets.

- [ ] **Step 1: Write failing mart tests**

```python
def test_repurchase_behavior_has_exact_horizons():
    horizons = connection.execute(
        text("SELECT DISTINCT horizon_days FROM marts.repurchase_behavior")
    ).scalars().all()
    assert sorted(horizons) == [30, 60, 90]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/sql/test_customer_value_repurchases.py -v --basetemp .pytest-tmp\customer-repurchase-red`

Expected: FAIL because both marts are missing.

- [ ] **Step 3: Implement governed marts**

Aggregate `marts.customer_360` by RFM segment with customer/revenue shares, average recency/frequency/monetary values, and lifecycle counts based on delivered-order frequency (1, 2, 3+). For repurchase behavior, identify first and strictly later delivered orders, create eligibility-safe 30/60/90 labels and disjoint 0–30, 31–60, 61–90, 91–180, 181+ interval buckets. First-purchase categories must preserve the correct customer denominator.

- [ ] **Step 4: Register queries, verify GREEN, and commit**

Run: `python -m pytest tests/sql/test_customer_value_repurchases.py tests/analytics/test_repository.py -v --basetemp .pytest-tmp\customer-repurchase-green`

Commit: `git add sql/marts/037_customer_value_analysis.sql sql/marts/038_repurchase_behavior.sql scripts/build_marts.py tests/sql/test_customer_value_repurchases.py src/analytics/repository.py tests/analytics/test_repository.py && git commit -m "feat: add customer value and repurchase behavior marts"`

### Task 4: Product, state, and delivery experience data

**Files:**
- Modify: `sql/marts/033_product_performance.sql`, `sql/marts/036_state_performance.sql`, `scripts/build_marts.py`
- Create: `sql/marts/039_delivery_rating_analysis.sql`
- Modify: `tests/sql/test_product_delivery_marts.py`, `src/analytics/repository.py`, `tests/analytics/test_repository.py`

**Interfaces:**
- Produces: category review measures, state delivery and review measures, and bounded delivery-delay buckets with order count and average review score.

- [ ] **Step 1: Write a failing state measure test**

```python
def test_state_performance_exposes_delivery_and_review_metrics():
    invalid = connection.execute(text("""
        SELECT COUNT(*) FROM marts.state_performance
        WHERE average_delivery_days < 0 OR average_review_score NOT BETWEEN 1 AND 5
    """)).scalar_one()
    assert invalid == 0
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py -v --basetemp .pytest-tmp\delivery-experience-red`

Expected: FAIL because the fields and delivery-rating mart are absent.

- [ ] **Step 3: Implement measures and repository methods**

Add `average_review_score` to product performance, `average_delivery_days` and `average_review_score` to state performance, and `delivery_rating_analysis` by delivery-delay bucket. Missing reviews stay `NULL`, never zero. Repository calls remain `_read_mart` calls with only fixed internal identifiers.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/sql/test_product_delivery_marts.py tests/analytics/test_repository.py -v --basetemp .pytest-tmp\delivery-experience-green`

Commit: `git add sql/marts/033_product_performance.sql sql/marts/036_state_performance.sql sql/marts/039_delivery_rating_analysis.sql scripts/build_marts.py tests/sql/test_product_delivery_marts.py src/analytics/repository.py tests/analytics/test_repository.py && git commit -m "feat: enrich product and delivery experience analysis"`

### Task 5: Chart factories and five Dashboard pages

**Files:**
- Modify: `src/visualization/charts.py`, `app/components/presentation.py`, `tests/visualization/test_charts.py`
- Modify: `app/Home.py`, `app/pages/1_经营总览.py` through `app/pages/5_商品与履约.py`, `app/components/layout.py`, `tests/visualization/test_dashboard_pages.py`

**Interfaces:**
- Produces: separate metric trend charts, grouped bars, horizontal ranks, bubble scatter, delivery-rating scatter, and fully rendered P1–P5 views.

- [ ] **Step 1: Write failing chart and page acceptance tests**

```python
def test_bubble_scatter_encodes_orders_as_marker_size():
    frame = pd.DataFrame({"gmv_growth_pct": [10.0], "item_revenue": [100.0], "order_count": [5]})
    figure = bubble_scatter_chart(frame, "gmv_growth_pct", "item_revenue", "order_count", "增长机会矩阵")
    assert figure.data[0].marker.size[0] == 5
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/visualization -v --basetemp .pytest-tmp\dashboard-charts-red`

Expected: FAIL because the factories and page-local controls are absent.

- [ ] **Step 3: Implement analytical reading paths**

P1: six KPIs, three stacked trends, top-10 category rank, state contribution. P2: growth KPIs, buyers/frequency/AOV driver views, new-versus-returning comparison, only truthful opportunity views. P3: lifecycle and segment-level RFM scatter. P4: 30/60/90 KPIs, cohort heatmap, interval bars, first-category rates. P5: category order/revenue matrix, state delivery-risk ranking/details, delivery-delay/rating scatter. Use a directly labelled state ranking as fallback unless bundled state geometry enables a tested filled map.

- [ ] **Step 4: Verify pages and application startup**

Run: `python -m pytest tests/visualization -v --basetemp .pytest-tmp\dashboard-pages-green`

Run: `python -m streamlit run app/Home.py --server.headless true --server.port 8502`

Expected: Streamlit prints a local URL without import errors; stop it after health validation.

- [ ] **Step 5: Commit**

Commit: `git add app src/visualization tests/visualization && git commit -m "feat: implement five-page business analytics dashboard"`

### Task 6: Learning record and full verification

**Files:**
- Modify: `docs/learning/week-2.md`
- Modify: `docs/analysis/findings.md` only for newly validated results.

- [ ] **Step 1: Record learning**

Explain mart grain, page-local filters, weighted aggregation, and why delivery/rating visuals only support association.

- [ ] **Step 2: Run full verification**

Run: `python -m pytest -v --basetemp .pytest-tmp\dashboard-design-full`

Run: `python -m ruff check app src tests scripts`

Run: `git diff --check`

Expected: test suite passes, Ruff has no diagnostics, and the diff has no whitespace errors.

- [ ] **Step 3: Commit documentation**

Commit: `git add docs/learning/week-2.md docs/analysis/findings.md && git commit -m "docs: record dashboard analysis learning"`
