# Streamlit 悬浮吸顶导航 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用悬浮吸顶导航替代默认 Streamlit 多页菜单，仅保留五个分析页入口。

**Architecture:** 新建共享导航组件，使用 `st.page_link` 保留 Streamlit 路由和键盘访问；主题 CSS 同时隐藏默认多页菜单并提供浮动、吸顶、当前页、焦点和响应式样式。主页和五个分析页复用同一组件，`Home.py` 不在导航中显示。

**Tech Stack:** Python 3.13, Streamlit, pytest, Ruff。

## Global Constraints

- 默认 Streamlit 多页菜单不可见，筛选侧栏及其控件必须保持可见。
- 导航仅包含五个分析页，不展示首页入口。
- 导航须采用浮动吸顶样式，包含当前页、悬停、可见键盘焦点和窄屏换行规则。
- 保持既有页面路由、查询、缓存、筛选、指标口径和空数据处理不变。

---

### Task 1: 共享悬浮导航与页面接入

**Files:**
- Create: `app/components/navigation.py`
- Modify: `app/components/layout.py`
- Modify: `app/Home.py`, `app/pages/1_经营总览.py`, `app/pages/2_增长诊断.py`, `app/pages/3_留存复购.py`, `app/pages/4_客户价值.py`, `app/pages/5_商品与履约.py`
- Modify: `tests/visualization/test_dashboard_pages.py`
- Create: `tests/visualization/test_navigation.py`

**Interfaces:**
- Produces: `render_navigation() -> None`, rendered through native `st.page_link` calls for the five existing page paths.
- Consumes: the shared `apply_dashboard_theme()` call already present at page startup.

- [ ] **Step 1: Write failing navigation tests**

```python
from pathlib import Path

from app.components.navigation import NAVIGATION_PAGES


def test_navigation_contains_only_five_analysis_pages():
    assert [path for path, _ in NAVIGATION_PAGES] == [
        "app/pages/1_经营总览.py", "app/pages/2_增长诊断.py",
        "app/pages/3_留存复购.py", "app/pages/4_客户价值.py",
        "app/pages/5_商品与履约.py",
    ]


def test_every_page_uses_shared_navigation():
    for path in [Path("app/Home.py"), *Path("app/pages").glob("*.py")]:
        assert "render_navigation" in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.13 -m pytest tests/visualization/test_navigation.py -v`

Expected: FAIL with missing `app.components.navigation`.

- [ ] **Step 3: Implement the native navigation and theme rules**

```python
NAVIGATION_PAGES = (
    ("app/pages/1_经营总览.py", "经营总览"),
    ("app/pages/2_增长诊断.py", "增长诊断"),
    ("app/pages/3_留存复购.py", "留存复购"),
    ("app/pages/4_客户价值.py", "客户价值"),
    ("app/pages/5_商品与履约.py", "商品与履约"),
)


def render_navigation() -> None:
    with st.container(key="floating-navigation"):
        for path, label in NAVIGATION_PAGES:
            st.page_link(path, label=label, use_container_width=True)
```

Add CSS in `apply_dashboard_theme()` that hides only `[data-testid="stSidebarNav"]`; styles the keyed navigation container as `position: sticky; top: 12px; z-index: 999;` with white translucent background, border, shadow, radius and wrapping links; includes `:hover`, `:focus-visible` and current-page rules. Import and call `render_navigation()` after `apply_dashboard_theme()` and before each page header.

- [ ] **Step 4: Run GREEN and regression checks**

Run: `py -3.13 -m pytest tests/visualization/test_navigation.py tests/visualization/test_dashboard_pages.py -v; py -3.13 -m ruff check app tests/visualization`

Expected: all tests PASS and Ruff reports no violations.

- [ ] **Step 5: Commit**

Run: `git add app/components/navigation.py app/components/layout.py app/Home.py app/pages tests/visualization/test_navigation.py tests/visualization/test_dashboard_pages.py && git commit -m "feat: add floating sticky dashboard navigation"`

### Task 2: Final validation

**Files:** none unless validation identifies an implementation defect.

- [ ] **Step 1: Run full test suite**

Run: `py -3.13 -m pytest -q --basetemp .pytest-basetemp`

Expected: PASS.

- [ ] **Step 2: Run lint and Streamlit startup check**

Run: `py -3.13 -m ruff check app tests/visualization; py -3.13 -m streamlit run app/Home.py --server.headless true --server.port 8503`

Expected: Ruff has no errors and Streamlit starts without an import or routing error; stop the server after startup.

- [ ] **Step 3: Inspect the acceptance criteria**

Confirm the floating navigation contains only the five analysis labels, default page navigation is hidden while the filter sidebar remains, and all six application files invoke `render_navigation` before their headers.
