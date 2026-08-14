# 无侧栏玻璃胶囊导航 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除 Streamlit 左侧栏和全部筛选控件，将五页导航改造成居中悬浮、滚动吸顶的玻璃胶囊。

**Architecture:** 保留现有 `navigation.py` 的原生路由链接，重写主题 CSS 使导航成为内容宽度自适应的居中组件。页面移除 `render_filters` 与筛选状态的依赖，改以 `DashboardFilters()` 作为默认全量口径。

**Tech Stack:** Python 3.13, Streamlit, pytest, Ruff。

## Global Constraints

- 左侧栏和全部筛选控件必须不可见且不再渲染。
- 导航仅包含五个分析页，不展示首页。
- 导航位于顶部中央、距顶约 48px，采用半透明白色、28px 圆角、细描边和柔和阴影；滚动后吸顶。
- 当前页强调，未选中页灰色，保留悬停、键盘焦点和窄屏换行。
- 不更改仓储查询、缓存、指标计算或 SQL；所有页面使用默认全量口径。

---

### Task 1: 删除筛选侧栏并重做导航胶囊

**Files:**
- Modify: `app/components/filters.py`, `app/components/layout.py`, `app/components/navigation.py`
- Modify: `app/pages/1_经营总览.py`, `app/pages/2_增长诊断.py`, `app/pages/3_留存复购.py`, `app/pages/4_客户价值.py`, `app/pages/5_商品与履约.py`
- Modify: `tests/visualization/test_dashboard_components.py`, `tests/visualization/test_dashboard_pages.py`, `tests/visualization/test_navigation.py`

- [ ] **Step 1: Write failing tests**

```python
def test_analysis_pages_do_not_render_or_import_filters():
    for page in Path("app/pages").glob("*.py"):
        content = page.read_text(encoding="utf-8")
        assert "render_filters" not in content
        assert "filters =" not in content

def test_navigation_css_hides_entire_sidebar_and_centers_glass_pill():
    content = Path("app/components/layout.py").read_text(encoding="utf-8")
    assert '[data-testid="stSidebar"] { display: none; }' in content
    assert "justify-content: center" in content
    assert "top: 48px" in content
    assert "border-radius: 28px" in content
```

- [ ] **Step 2: Run RED**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_pages.py tests/visualization/test_navigation.py -v`

Expected: FAIL because pages still import/render filters and the existing CSS preserves the sidebar.

- [ ] **Step 3: Implement the minimal redesign**

Remove `render_filters` from the five analysis pages and call each loader with `DashboardFilters()`. Remove unused filter imports; retain the `DashboardFilters` type only where cache loader annotations use it. Replace sidebar styles with `[data-testid="stSidebar"] { display: none; }`. Make the navigation wrapper sticky at `top: 48px`, center its inner container with `justify-content: center`, use `width: fit-content; max-width: calc(100vw - 2rem)`, glass background, `border-radius: 28px`, soft shadow and 180ms hover transition. Remove `use_container_width=True` from `st.page_link` so link widths follow content; preserve current/focus rules.

- [ ] **Step 4: Run GREEN**

Run: `py -3.13 -m pytest tests/visualization/test_dashboard_components.py tests/visualization/test_dashboard_pages.py tests/visualization/test_navigation.py -v; py -3.13 -m ruff check app tests/visualization`

Expected: PASS with no Ruff errors.

- [ ] **Step 5: Commit**

Run: `git add app/components/filters.py app/components/layout.py app/components/navigation.py app/pages tests/visualization && git commit -m "feat: remove sidebar and refine glass navigation"`

### Task 2: Final validation

- [ ] **Step 1: Run the full suite**

Run: `py -3.13 -m pytest -q --basetemp .pytest-basetemp`

Expected: PASS.

- [ ] **Step 2: Smoke test startup**

Run: `py -3.13 -m streamlit run app/Home.py --server.headless true --server.port 8505`

Expected: the app starts with no import or page-route error; terminate it after startup.
