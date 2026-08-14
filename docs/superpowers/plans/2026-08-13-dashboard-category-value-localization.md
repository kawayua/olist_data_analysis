# Dashboard 品类值中文化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Dashboard 中的 Olist 英文品类编码显示为中文品类名。

**Architecture:** `presentation.py` 提供 `product_category` 与 `first_purchase_category` 的共用中文值映射；表格和图表工厂都只使用展示副本，因此仓库查询和原始 DataFrame 保持英文编码。

**Tech Stack:** Python 3.13、pandas、Plotly Express、pytest。

## Global Constraints

- 不修改数据库表、SQL 集市、查询结果中的原始品类编码、筛选逻辑或指标计算。
- 未知编码原样显示，不作猜测性翻译。

---

### Task 1: 表格与柱状图品类值中文化

**Files:**
- Modify: `app/components/presentation.py`
- Modify: `tests/visualization/test_dashboard_components.py`
- Modify: `tests/visualization/test_charts.py`

**Interfaces:**
- Consumes: `display_dataframe(frame: pd.DataFrame) -> pd.DataFrame`
- Produces: `display_value(column: str, value: object) -> object` 对两个品类字段返回中文值。

- [ ] **Step 1: Write the failing tests**

```python
def test_display_dataframe_translates_product_category_values() -> None:
    displayed = display_dataframe(pd.DataFrame({"product_category": ["health_beauty"]}))
    assert displayed.iloc[0, 0] == "美妆与健康"

def test_ranked_bar_chart_translates_first_purchase_category_axis_values() -> None:
    frame = pd.DataFrame({"first_purchase_category": ["bed_bath_table"], "repurchase_rate_pct": [10.0]})
    figure = ranked_bar_chart(frame, "first_purchase_category", "repurchase_rate_pct", "首购复购率")
    assert figure.data[0].x[0] == "床品、卫浴与餐桌"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_components.py::test_display_dataframe_translates_product_category_values tests/visualization/test_charts.py::test_ranked_bar_chart_translates_first_purchase_category_axis_values -v`

Expected: FAIL because the category codes have no Chinese value mapping and bar charts receive raw x values.

- [ ] **Step 3: Write minimal implementation**

Add a complete Olist category-code mapping to `CATEGORY_DISPLAY_VALUES` and share it between `product_category` and `first_purchase_category`. Pass a localized copy of the x category field to `px.bar`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_components.py tests/visualization/test_charts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Stage the presentation module and both visualization test modules; commit as `feat: localize dashboard category values`.

### Task 2: 气泡图品类图例中文化与验证

**Files:**
- Modify: `src/visualization/charts.py`
- Modify: `tests/visualization/test_charts.py`

**Interfaces:**
- Consumes: `localized_chart_frame(frame, color)` and `display_value`.
- Produces: category-coloured scatter traces whose legend labels are Chinese category names.

- [ ] **Step 1: Write the failing test**

```python
def test_bubble_chart_translates_product_category_legend_values() -> None:
    frame = pd.DataFrame({
        "order_count": [5], "item_revenue": [100.0],
        "average_review_score": [4.0], "product_category": ["toys"],
    })
    figure = bubble_scatter_chart(frame, "order_count", "item_revenue", "average_review_score", "品类表现", color="product_category")
    assert figure.data[0].name == "玩具"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/visualization/test_charts.py::test_bubble_chart_translates_product_category_legend_values -v`

Expected: FAIL because `product_category` has no value mapping.

- [ ] **Step 3: Write minimal implementation**

Reuse the Task 1 mapping through `localized_chart_frame`; no page or query changes are required.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/visualization/test_charts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Stage changed chart and test files; commit as `test: cover category legend localization`.

### Task 3: 完整验证

**Files:**
- Verify only: `tests/visualization/`
- Verify only: `app/Home.py`

**Interfaces:**
- Consumes: localized table and chart factories.
- Produces: a verified Dashboard with Chinese category values.

- [ ] **Step 1: Run visualisation tests**

Run: `py -3.13 -m pytest tests/visualization -v --basetemp "$env:TEMP\\dashboard-category-labels-20260813"`

Expected: PASS.

- [ ] **Step 2: Run static checks**

Run: `py -3.13 -m ruff check app/components/presentation.py src/visualization/charts.py tests/visualization`

Expected: PASS.

- [ ] **Step 3: Start the Dashboard smoke test**

Run: `C:\Program Files\Python313\python.exe -m streamlit run app/Home.py --server.headless true --server.port 8502`

Expected: the process listens on port 8502 without an import or page-loading error.
