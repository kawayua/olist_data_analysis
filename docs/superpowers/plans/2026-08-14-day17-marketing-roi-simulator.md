# Day 17 Marketing ROI Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已校准的客户复购概率转为可调假设下的增量利润与 ROI 触达建议。

**Architecture:** `src/ml/roi.py` 负责输入校验、概率排序、预算约束与情景计算；Streamlit 页面只提供参数控件和展示。模拟器只计算增量收益，提升率由用户假设而非模型因果结论。

**Tech Stack:** Python 3.13, pandas, numpy, Streamlit, Plotly, pytest, Ruff。

## Global Constraints

- 只计算营销增量复购、增量收入、净增量利润和 ROI；不把自然复购收入计为营销收益。
- 默认推荐净增量利润最高的方案，ROI 仅作辅助指标。
- 预算、触达成本必须大于零；收入非负；提升率在 `[0, 1]` 且保守、基准、乐观递增。
- 页面必须明确提升率是待 A/B 测试验证的业务假设，预测不代表确定复购或因果效果。
- 不修改或提交既有无关的未提交文件、测试临时目录或运行产物。

---

## File Structure

- Create: `src/ml/roi.py` — 纯计算模型、情景结果与输入校验。
- Create: `tests/ml/test_roi.py` — 公式、预算、排序和异常边界测试。
- Create: `app/pages/6_营销ROI模拟器.py` — 参数输入、KPI、情景表、利润曲线和限制说明。
- Modify: `docs/learning/week-2.md` — Day 17 增量利润与因果限制学习记录。

### Task 1: 建立可测试的 ROI 情景计算服务

**Files:** Create `src/ml/roi.py`; Create `tests/ml/test_roi.py`

**Interfaces:**
- Produces `Scenario(name: str, uplift_rate: float)` and `SimulationResult(scenario: str, contacted_customers: int, incremental_repurchases: float, incremental_revenue: float, marketing_cost: float, net_incremental_profit: float, roi: float)`。
- Produces `simulate_roi(probabilities: pd.Series, budget: float, contact_cost: float, average_repurchase_revenue: float, scenarios: tuple[Scenario, ...], max_contact_fraction: float) -> list[SimulationResult]`。

- [ ] **Step 1: 写失败测试**

```python
def test_simulator_calculates_incremental_profit_for_top_customers():
    results = simulate_roi(pd.Series([0.8, 0.4, 0.1]), 20, 10, 100,
        (Scenario("基准", 0.1),), 1.0)
    result = results[0]
    assert result.contacted_customers == 2
    assert result.incremental_repurchases == 0.12
    assert result.net_incremental_profit == -8.0
```

增加测试：预算只能触达前 N 位、同一概率输入下较高提升率有较高利润、负预算/成本、越界或乱序提升率抛出 `ValueError`，以及预算不足触达一人时抛出 `ValueError("no executable contact plan")`。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/ml/test_roi.py -v --basetemp "$env:TEMP\day17-roi-red"`；预期 ImportError。

- [ ] **Step 3: 最小实现**

按概率降序取 `min(floor(budget/contact_cost), floor(len(probabilities)*max_contact_fraction), len(probabilities))` 个客户；每情景用 `probability_sum * uplift_rate` 计算增量复购，再依设计文档公式计算结果。输入验证必须先于计算；禁止读取标签或未来字段。

- [ ] **Step 4: 验证 GREEN**

运行：`py -3.13 -m pytest tests/ml/test_roi.py -v --basetemp "$env:TEMP\day17-roi-green"`；预期 PASS。

- [ ] **Step 5: 提交**

`git add src/ml/roi.py tests/ml/test_roi.py; git commit -m "feat: add marketing roi simulation service"`

### Task 2: 建立利润最大化的策略搜索

**Files:** Modify `src/ml/roi.py`; Modify `tests/ml/test_roi.py`

**Interfaces:**
- Produces `recommend_profit_maximizing_plan(probabilities, budget_options, contact_cost, average_repurchase_revenue, baseline_scenario, max_contact_fraction) -> SimulationResult`。

- [ ] **Step 1: 写失败测试**

```python
def test_recommendation_uses_net_incremental_profit_not_roi():
    result = recommend_profit_maximizing_plan(
        pd.Series([0.9, 0.8, 0.7]), (10, 20, 30), 10, 100,
        Scenario("基准", 0.5), 1.0)
    assert result.contacted_customers == 3
```

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/ml/test_roi.py::test_recommendation_uses_net_incremental_profit_not_roi -v --basetemp "$env:TEMP\day17-search-red"`；预期 ImportError。

- [ ] **Step 3: 最小实现与 GREEN**

对每个预算调用 `simulate_roi` 的基准情景，以 `net_incremental_profit` 最大值选择；并列时选择较低预算。运行同一命令，预期 PASS；再运行 `py -3.13 -m ruff check src/ml tests/ml`。

- [ ] **Step 4: 提交**

`git add src/ml/roi.py tests/ml/test_roi.py; git commit -m "feat: recommend profit maximizing marketing plan"`

### Task 3: 接入 Streamlit 页面与学习记录

**Files:** Create `app/pages/6_营销ROI模拟器.py`; Modify `docs/learning/week-2.md`

**Interfaces:**
- Consumes: Day 16 model bundle、当前客户特征和 `simulate_roi` / `recommend_profit_maximizing_plan`。
- Produces: 中文参数控件、三情景 KPI/表格、利润曲线、五位代表客户与因果限制说明。

- [ ] **Step 1: 写页面辅助函数失败测试**

在 `tests/ml/test_roi.py` 增加 `test_profit_curve_contains_each_budget_option`，针对 `build_profit_curve(probabilities, budgets, ...)` 断言 DataFrame 含 `预算`、`净增量利润`、`ROI` 三列且行数等于预算选项数。

- [ ] **Step 2: 验证 RED、实现、GREEN**

先运行该单测确认函数不存在；在 `src/ml/roi.py` 用基准情景逐预算构造曲线。页面以 `st.number_input` 收集参数，用 `st.cache_data` 缓存不含用户输入的模型评分读取；输入参数直接传给服务。展示推荐方案、保守/基准/乐观表、Plotly 折线、五名最高概率客户的 `customer_key` 与概率。始终显示“提升率是业务假设，需 A/B 测试验证；预测关联不代表营销因果效果”。

- [ ] **Step 3: 全量验证与提交**

运行：

```powershell
py -3.13 -m pytest tests/ml tests/sql -v --basetemp "$env:TEMP\day17-full"
py -3.13 -m ruff check src/ml app/pages/6_营销ROI模拟器.py tests/ml
```

在 `week-2.md` 追加 Day 17：为什么用增量而非总收入、为何利润最大化不同于 ROI 最大化、为何 uplift 需 A/B 验证。提交：`git add app/pages/6_营销ROI模拟器.py src/ml/roi.py tests/ml/test_roi.py docs/learning/week-2.md; git commit -m "feat: add marketing roi simulator page"`。

## Self-Review

- Spec coverage: Task 1 实现增量公式、预算与输入边界；Task 2 落实利润最大化；Task 3 提供页面、情景展示、代表客户、时间/因果限制和学习记录。
- Placeholder scan: 每项均包含函数名、输入、断言、命令与提交范围，没有未定实现项。
- Type consistency: 页面和策略搜索均调用同一 `Scenario`、`SimulationResult` 与 `simulate_roi` 接口。
