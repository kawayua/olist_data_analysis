# Streamlit 卡片化数据驾驶舱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Olist Streamlit 应用升级为专业、克制的卡片化数据驾驶舱，并将图表和数据表展示字段中文化。

**Architecture:** 保持仓储、SQL 和 DataFrame 内部字段不变，在展示层集中增加列名映射与 Plotly 图表工厂。`app.components.layout` 负责统一主题、卡片与标题；页面只组合共享布局、现有查询结果和图表工厂。

**Tech Stack:** Python 3.11+, Streamlit 1.40+, pandas 2.2+, Plotly 5.24+, pytest 8+, Ruff。

## Global Constraints

- 不修改 SQL、仓储查询、指标计算或底层 DataFrame 英文字段名。
- 图表标题、坐标轴、图例、悬浮提示、文本标签和数据表列名必须使用中文。
- 保持既有五个页面、筛选行为和空数据提示；不新增第三方依赖。
- 使用浅灰蓝背景、白色卡片、深蓝主色和琥珀预警色，并通过 pytest 和 Ruff。

---

### Task 1: 中文展示层与布局组件

**Files:**
- Create: `app/components/presentation.py`
- Create: `app/components/layout.py`
- Modify: `app/components/kpis.py`, `app/components/filters.py`
- Test: `tests/visualization/test_dashboard_components.py`

**Interfaces:**
- Produces: `display_label(column: str) -> str`、`display_dataframe(frame: pd.DataFrame) -> pd.DataFrame`、`apply_dashboard_theme() -> None`、`render_page_header(title: str, description: str, scope: str) -> None`、`render_insight(title: str, body: str) -> None`。

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd
from app.components.presentation import display_dataframe, display_label

def test_display_dataframe_renames_without_mutating_source():
    source = pd.DataFrame({"item_revenue": [123.0], "customer_state": ["SP"]})
    assert list(display_dataframe(source).columns) == ["商品金额", "客户所在州"]
    assert list(source.columns) == ["item_revenue", "customer_state"]

def test_display_label_keeps_unknown_column_name():
    assert display_label("unmapped_metric") == "unmapped_metric"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/visualization/test_dashboard_components.py -v`

Expected: FAIL with `ModuleNotFoundError: app.components.presentation`.

- [ ] **Step 3: Write the minimal implementation**

```python
CHINESE_COLUMNS = {
    "item_revenue": "商品金额", "order_count": "订单数",
    "customer_count": "客户数", "customer_state": "客户所在州",
    "product_category": "商品品类", "customer_segment": "客户分群",
    "delivery_status": "履约状态", "average_review_score": "平均评分",
    "month_start": "月份", "retention_rate_pct": "留存率（%）",
}
def display_label(column: str) -> str:
    return CHINESE_COLUMNS.get(column, column)
def display_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns=CHINESE_COLUMNS)
```

Implement `layout.py` with one CSS injection for app background, cards, sidebar headings and responsive KPI spacing. Render a title/description/scope header and insight cards with visible text labels. Convert `render_kpis` to shared cards. Group filters under “时间范围”“分析维度”“数据口径” without changing returned filter values.

- [ ] **Step 4: Run the test and confirm it passes**

Run: `pytest tests/visualization/test_dashboard_components.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add app/components/presentation.py app/components/layout.py app/components/kpis.py app/components/filters.py tests/visualization/test_dashboard_components.py && git commit -m "feat: add dashboard presentation components"`

### Task 2: 中文 Plotly 图表工厂

**Files:**
- Modify: `src/visualization/charts.py`
- Test: `tests/visualization/test_charts.py`

**Interfaces:**
- Consumes: 原始 DataFrame 字段与 `display_label`。
- Produces: `line_chart(frame, x, y, title) -> Figure`、`ranked_bar_chart(frame, x, y, title, color=None) -> Figure`、`retention_heatmap(matrix: pd.DataFrame) -> Figure`。

- [ ] **Step 1: Write failing chart tests**

```python
def test_line_chart_uses_chinese_axis_and_hover_labels():
    frame = pd.DataFrame({"month_start": ["2024-01-01"], "item_revenue": [100.0]})
    figure = line_chart(frame, x="month_start", y="item_revenue", title="月度商品金额")
    assert figure.layout.xaxis.title.text == "月份"
    assert figure.layout.yaxis.title.text == "商品金额"
    assert "商品金额" in figure.data[0].hovertemplate

def test_ranked_bar_chart_sorts_descending():
    frame = pd.DataFrame({"product_category": ["A", "B"], "item_revenue": [10.0, 20.0]})
    figure = ranked_bar_chart(frame, x="product_category", y="item_revenue", title="品类排名")
    assert list(figure.data[0].x) == ["B", "A"]
    assert figure.layout.xaxis.title.text == "商品品类"
```

- [ ] **Step 2: Run them and confirm failure**

Run: `pytest tests/visualization/test_charts.py -v`

Expected: FAIL because labels are raw fields and `ranked_bar_chart` is absent.

- [ ] **Step 3: Implement factories and shared chart theme**

```python
def ranked_bar_chart(frame, x, y, title, color=None):
    ordered = frame.sort_values(y, ascending=False)
    figure = px.bar(ordered, x=x, y=y, color=color, text=y,
                    labels={name: display_label(name) for name in ordered.columns}, title=title)
    return apply_chart_layout(figure, y)
```

Implement `apply_chart_layout` with white plot/paper, dark-blue type, light grid, compact legend, `R$%{y:,.0f}` income hover format and mapped labels. Build `retention_heatmap` with `px.imshow`, “Cohort 首购月份”“距首购月数”“留存率（%）” axis/color labels.

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/visualization/test_charts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/visualization/charts.py tests/visualization/test_charts.py && git commit -m "feat: localize dashboard charts"`

### Task 3: 重构主页和五个分析页面

**Files:**
- Modify: `app/Home.py`, `app/pages/1_经营总览.py`, `app/pages/2_增长诊断.py`, `app/pages/3_留存复购.py`, `app/pages/4_客户价值.py`, `app/pages/5_商品与履约.py`
- Test: `tests/visualization/test_dashboard_pages.py`

**Interfaces:**
- Consumes: Tasks 1–2 的布局、展示和图表工厂，以及既有仓储方法。
- Produces: 每页统一标题、KPI、图表/洞察卡和中文表格；缓存、查询和空数据分支保持不变。

- [ ] **Step 1: Write failing structural test**

```python
def test_every_dashboard_page_uses_shared_card_layout():
    for page in Path("app/pages").glob("*.py"):
        content = page.read_text(encoding="utf-8")
        assert "render_page_header" in content
        assert "apply_dashboard_theme" in content

def test_dataframe_pages_use_chinese_display_layer():
    for page in ["app/Home.py", "app/pages/3_留存复购.py", "app/pages/5_商品与履约.py"]:
        assert "display_dataframe" in Path(page).read_text(encoding="utf-8")
```

- [ ] **Step 2: Run it and confirm failure**

Run: `pytest tests/visualization/test_dashboard_pages.py -v`

Expected: FAIL because existing pages do not use the shared layout.

- [ ] **Step 3: Implement card layout page-by-page**

Call `apply_dashboard_theme()` at every page startup; replace `st.title` with `render_page_header`. Use `st.columns` and `st.container(border=True)` for charts and `render_insight` for the existing interpretation. Replace `st.bar_chart` and inline `px.bar` with `ranked_bar_chart`, retain the growth `line_chart`, and use `retention_heatmap` with the renamed cohort matrix. Every `st.dataframe` must receive `display_dataframe(...)`; replace delivery values `late`/`on_time` with `延迟`/`按时` only in a copied display frame. Preserve cache decorators, filters and repository calls.

- [ ] **Step 4: Run focused verification**

Run: `pytest tests/visualization/test_dashboard_pages.py tests/visualization/test_dashboard_components.py tests/visualization/test_charts.py -v; ruff check app src/visualization tests/visualization`

Expected: all tests PASS; Ruff returns zero violations.

- [ ] **Step 5: Commit**

Run: `git add app/Home.py app/pages tests/visualization/test_dashboard_pages.py && git commit -m "feat: rebuild analytics pages as dashboard cards"`

### Task 4: 端到端验证

**Files:** none unless checks reveal a defect.

- [ ] **Step 1: Run full tests**

Run: `pytest -q`

Expected: PASS with zero failed tests.

- [ ] **Step 2: Run lint**

Run: `ruff check app src/visualization tests/visualization`

Expected: no lint errors.

- [ ] **Step 3: Smoke-test Streamlit startup**

Run: `streamlit run app/Home.py --server.headless true --server.port 8501`

Expected: server starts without import, encoding or Plotly configuration errors; stop it after startup confirms.

- [ ] **Step 4: Inspect acceptance criteria**

Confirm all pages use Chinese headers, KPI labels, card layout and Chinese Plotly titles/axes/legend/hover labels; confirm the home, cohort and delivery tables show no raw technical column names.
