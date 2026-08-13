# Dashboard 中文展示标签 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Dashboard 表格、图表坐标轴、图例和悬停提示中的技术字段及分类值统一显示为中文。

**Architecture:** 英文内部字段保持不变，`presentation.py` 集中维护字段和分类值展示映射。`charts.py` 通过该展示层生成坐标轴、图例和按指标类型格式化的中文悬停提示。

**Tech Stack:** Python 3.13、pandas、Plotly Express、pytest、Streamlit。

## Global Constraints

- 不修改 SQL 集市、仓库查询、指标计算、筛选逻辑、图表类型或页面布局。
- 所有面向 Dashboard 读者的字段名称与已定义分类值均使用中文。
- `display_dataframe` 不得修改传入的 DataFrame。

---

### Task 1: 完整的表格字段与分类值中文化

**Files:**
- Modify: `app/components/presentation.py`
- Modify: `tests/visualization/test_dashboard_components.py`

**Interfaces:**
- Consumes: `display_dataframe(frame: pd.DataFrame) -> pd.DataFrame`
- Produces: `display_value(column: str, value: object) -> object`，供表格和图表复用。

- [ ] **Step 1: Write the failing test**

```python
def test_display_dataframe_translates_columns_and_segment_values() -> None:
    frame = pd.DataFrame({
        "customer_segment": ["high_value"],
        "customer_share_pct": [12.5],
        "repeat_customer_item_revenue": [100.0],
    })
    result = display_dataframe(frame)
    assert result.columns.tolist() == ["客户分群", "客户占比（%）", "复购客户商品金额"]
    assert result.iloc[0, 0] == "高价值客户"
    assert frame.columns.tolist() == [
        "customer_segment", "customer_share_pct", "repeat_customer_item_revenue"
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_components.py::test_display_dataframe_translates_columns_and_segment_values -v`

Expected: FAIL because the new fields and the `high_value` display value have no translation.

- [ ] **Step 3: Write minimal implementation**

Add every field rendered by the five Dashboard pages to `CHINESE_COLUMNS`; introduce `CATEGORY_DISPLAY_VALUES` and `display_value`. Apply `display_value` to a deep copy in `display_dataframe` before renaming its columns.

```python
CATEGORY_DISPLAY_VALUES = {"customer_segment": {"high_value": "高价值客户"}}

def display_value(column: str, value: object) -> object:
    return CATEGORY_DISPLAY_VALUES.get(column, {}).get(value, value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_components.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Stage `app/components/presentation.py` and `tests/visualization/test_dashboard_components.py`; commit as `feat: localize dashboard table fields`.

### Task 2: 图表中文坐标轴、图例与悬停提示

**Files:**
- Modify: `src/visualization/charts.py`
- Modify: `tests/visualization/test_charts.py`

**Interfaces:**
- Consumes: `display_label(column: str) -> str` and `display_value(column: str, value: object) -> object`
- Produces: chart factories with Chinese labels for Dashboard-visible content.

- [ ] **Step 1: Write the failing test**

```python
def test_bubble_chart_uses_chinese_axis_and_legend_labels() -> None:
    frame = pd.DataFrame({
        "average_frequency_orders": [2.0],
        "average_monetary_item_revenue": [100.0],
        "customer_count": [5],
        "customer_segment": ["high_value"],
    })
    figure = bubble_scatter_chart(
        frame, "average_frequency_orders", "average_monetary_item_revenue",
        "customer_count", "客户价值", color="customer_segment"
    )
    assert figure.layout.xaxis.title.text == "平均购买次数"
    assert figure.layout.yaxis.title.text == "平均客户商品金额"
    assert figure.layout.legend.title.text == "客户分群"
    assert "平均购买次数" in figure.data[0].hovertemplate
    assert "average_frequency_orders" not in figure.data[0].hovertemplate
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/visualization/test_charts.py::test_bubble_chart_uses_chinese_axis_and_legend_labels -v`

Expected: FAIL because chart input does not translate category values and the existing hover formatter is generic.

- [ ] **Step 3: Write minimal implementation**

Pass a localized copy of the selected category column to Plotly. Replace the fixed `R$%{y:,.0f}` hover template with metric-aware templates: `R$` for revenue, `%` for rates, `分` for review scores, and no artificial currency unit for counts and days. Retain `display_label` for axes and legend titles.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/visualization/test_charts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Stage `src/visualization/charts.py` and `tests/visualization/test_charts.py`; commit as `feat: localize dashboard chart labels`.

### Task 3: 全量验证与页面启动检查

**Files:**
- Verify only: `app/Home.py`
- Verify only: `tests/visualization/`

**Interfaces:**
- Consumes: completed display and chart factories.
- Produces: a verified Dashboard with localized reader-facing content.

- [ ] **Step 1: Run visualisation tests**

Run: `py -3.13 -m pytest tests/visualization -v --basetemp "$env:TEMP\\dashboard-labels-20260813"`

Expected: PASS.

- [ ] **Step 2: Run static checks**

Run: `py -3.13 -m ruff check app/components/presentation.py src/visualization/charts.py tests/visualization`

Expected: PASS.

- [ ] **Step 3: Start the Dashboard for a smoke test**

Run: `py -3.13 -m streamlit run app/Home.py --server.headless true --server.port 8502`

Expected: Streamlit reports a local URL and no import or page-loading error.

- [ ] **Step 4: Commit verification-ready changes**

Stage only the presentation, chart and visualisation test files; commit as `test: verify dashboard Chinese presentation`.
