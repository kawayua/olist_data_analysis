# Day 19 可审计分析 Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可审计、有界、可离线评测的 LangChain 协议型分析 Agent 与 Streamlit 问数页面。

**Architecture:** `AnalysisAgent` 保持显式循环和工具轨迹；`evaluation` 仅以 fake client/tools 复现黄金问题；页面只消费 `AgentAnswer`，无配置时加载明确标注的演示对象。LangChain 仅存在于 Day 18 client 的消息和工具协议层。

**Tech Stack:** Python 3.13、Pydantic、LangChain Core、PyYAML、Streamlit、Plotly、pytest、Ruff。

---

### Task 1: 有界循环与审计回答

**Files:** Create `src/agent/orchestrator.py`, `tests/agent/test_orchestrator.py`.

- [ ] **Step 1: 写核心失败测试**

```python
def test_agent_executes_registered_tools_and_returns_audit_fields():
    client = ScriptedClient([
        response("", [call("m1", "get_metric_definition", {"name": "item_revenue"})]),
        response("商品金额为 100。", []),
    ])
    answer = AnalysisAgent(client, FakeTools(), max_steps=4).run("销售额？")
    assert [item.name for item in answer.tool_trace] == ["get_metric_definition"]
    assert answer.answer == "商品金额为 100。"
    assert answer.metric_definition["name"] == "item_revenue"
```

- [ ] **Step 2: 验证 RED**

Run: `py -3.13 -m pytest tests/agent/test_orchestrator.py::test_agent_executes_registered_tools_and_returns_audit_fields -v`

Expected: FAIL，`src.agent.orchestrator` 不存在。

- [ ] **Step 3: 实现最小状态机**

定义冻结 dataclass `ToolTrace(name, arguments, status, elapsed_ms, result_summary)` 和 `AgentAnswer(answer, tool_trace, sql=None, metric_definition=None, data_range=None, limitations=(), rows=None, chart=None)`。`AnalysisAgent.run` 建立 system/user messages，调用 `client.complete(messages, tools.definitions())`；只派发五个 definitions 中存在的名称，工具调用结果写成 role=`tool` 的 JSON 文本。以 Pydantic `BaseModel` 为每个工具定义严格参数 schema；未知工具、参数错误和执行异常记录结构化错误，不泄露原异常。最多 6 步，同一规范化 `(name, arguments)` 连续失败两次返回安全失败；达到上限也返回限制说明。

- [ ] **Step 4: 增加边界 RED→GREEN 测试**

覆盖未知工具不执行、无效参数不执行、连续两次相同失败停止、超过 max_steps 停止、SQL/rows/chart/metric result 被提取到 `AgentAnswer`，并运行：

```powershell
py -3.13 -m pytest tests/agent/test_orchestrator.py -v
py -3.13 -m ruff check src/agent/orchestrator.py tests/agent/test_orchestrator.py
```

Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add src/agent/orchestrator.py tests/agent/test_orchestrator.py
git commit -m "feat: add bounded audited analysis agent"
```

### Task 2: 黄金问题与确定性评测

**Files:** Create `src/agent/evaluation.py`, `configs/agent_questions.yml`, `scripts/evaluate_agent.py`, `tests/agent/test_evaluation.py`.

- [ ] **Step 1: 写失败测试**

```python
def test_fake_evaluation_writes_rejection_and_tool_metrics(tmp_path):
    report = evaluate_agent(FakeAgent(), [golden_case("拒绝删除", should_reject=True)], tmp_path / "evaluation.json")
    assert report.rejection_accuracy == 1.0
    assert (tmp_path / "evaluation.json").exists()
```

- [ ] **Step 2: 验证 RED**

Run: `py -3.13 -m pytest tests/agent/test_evaluation.py -v`

Expected: FAIL，`src.agent.evaluation` 不存在。

- [ ] **Step 3: 实现评测与 YAML**

定义 `GoldenCase` 和 `EvaluationReport`，读取 YAML 的至少 30 条案例，类别覆盖增长、留存、客户、商品、履约、预测、模拟、不可回答、恶意 SQL。计算工具选择、SQL 成功、数值准确、拒绝准确、平均延迟与估算成本；JSON 使用 UTF-8。`scripts/evaluate_agent.py --mode fake` 只构造 deterministic fake agent 并写 `artifacts/agent/evaluation.json`；`--mode live` 必须检查 `Settings` 已配置才允许运行。

- [ ] **Step 4: GREEN 与提交**

```powershell
py -3.13 -m pytest tests/agent/test_evaluation.py -v
py -3.13 scripts/evaluate_agent.py --mode fake
git add src/agent/evaluation.py configs/agent_questions.yml scripts/evaluate_agent.py tests/agent/test_evaluation.py
git commit -m "feat: add deterministic analytics agent evaluation"
```

Expected: PASS，生成 `artifacts/agent/evaluation.json`，恶意 SQL 的拒绝率为 100%。

### Task 3: AI 分析助手页面和安全演示

**Files:** Create `app/pages/7_AI分析助手.py`, `tests/visualization/test_ai_assistant.py`; modify `app/components/navigation.py` only to加入页面入口。

- [ ] **Step 1: 写失败测试**

```python
def test_demo_answer_is_explicitly_labelled_and_never_calls_model():
    demo = build_demo_answer()
    assert "演示数据" in demo.answer
    assert demo.tool_trace
```

- [ ] **Step 2: 验证 RED**

Run: `py -3.13 -m pytest tests/visualization/test_ai_assistant.py -v`

Expected: FAIL，页面模块或 `build_demo_answer` 不存在。

- [ ] **Step 3: 实现页面**

页面复用 `render_navigation()` 与既有 layout；`is_configured` 仅在 Key 与 model 都非空时允许实时 `AnalysisAgent`。无配置分支返回固定 `AgentAnswer`，在标题和回答区显示“演示数据，非实时模型回答”，不实例化或调用 client。实时回答展示文本、`rows` DataFrame、Plotly figure、SQL、指标口径、时间范围、限制，并用 `st.expander` 展示轨迹。导航新增“AI分析助手”。

- [ ] **Step 4: GREEN 与提交**

```powershell
py -3.13 -m pytest tests/visualization/test_ai_assistant.py tests/visualization/test_navigation.py -v
py -3.13 -m ruff check app/pages/7_AI分析助手.py app/components/navigation.py tests/visualization
git add app/pages/7_AI分析助手.py app/components/navigation.py tests/visualization/test_ai_assistant.py tests/visualization/test_navigation.py
git commit -m "feat: add safe AI analytics assistant page"
```

### Task 4: 集成验证与学习记录

**Files:** Modify `docs/learning/week-2.md`.

- [ ] **Step 1: 全量验证**

```powershell
py -3.13 -m pytest tests/agent tests/visualization -v --basetemp "$env:TEMP\day19-final"
py -3.13 scripts/evaluate_agent.py --mode fake
py -3.13 -m ruff check src/agent tests/agent app/pages scripts
git check-ignore -v .env
git diff --check
```

Expected: 全部 PASS；fake 评测 JSON 存在；`.env` 未追踪。

- [ ] **Step 2: 记录并提交**

记录 LangChain 协议与自定义循环的区别、工具轨迹如何可审计、黄金集如何防止“看起来合理”、为何 fake 模式不花费 API 成本、演示与实时结果的边界。然后：

```powershell
git add docs/learning/week-2.md artifacts/agent/evaluation.json
git commit -m "docs: record Day 19 agent evaluation learning"
```
