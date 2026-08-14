# Floating Navigation Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让六个分析页面入口在单行顶部悬浮导航中完整可见。

**Architecture:** 只调整共享导航 CSS 和导航测试；保留 sticky、玻璃卡片、链接状态与单行布局。

**Tech Stack:** Streamlit, CSS, pytest, Ruff。

## Global Constraints

- 保持单行顶部悬浮，不折行、不裁切。
- 六个导航链接等宽分配；容器扩大到适配六个入口的视口宽度。
- 不修改页面业务逻辑或既有无关文件。

### Task 1: 扩大共享导航容器

**Files:** Modify `app/components/layout.py`; Modify `tests/visualization/test_navigation.py`

- [ ] **Step 1: 写失败测试**

在导航测试中断言 CSS 包含 `width: min(100%, 760px)`、`flex: 1 1 0`、`flex-wrap: nowrap` 与 `overflow-x: auto`。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/visualization/test_navigation.py -v --basetemp "$env:TEMP\nav-width-red"`；预期新断言失败。

- [ ] **Step 3: 最小实现**

将浮动导航和内部横向块宽度改为 `min(100%, 760px)`，保留 `flex-wrap: nowrap`；让每个页面链接为 `flex: 1 1 0`、文字居中；内部块加 `overflow-x: auto`，确保窄屏也不会裁切。

- [ ] **Step 4: 验证 GREEN**

运行：

```powershell
py -3.13 -m pytest tests/visualization/test_navigation.py -v --basetemp "$env:TEMP\nav-width-green"
py -3.13 -m ruff check app/components/layout.py tests/visualization/test_navigation.py
```

- [ ] **Step 5: 提交**

`git add app/components/layout.py tests/visualization/test_navigation.py; git commit -m "fix: widen floating dashboard navigation"`

## Self-Review

计划只修改共享样式和行为测试，满足单行、悬浮、六等分及窄屏不裁切要求。
