# Day 18 LangChain 受控 Agent 工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用 LangChain 的 OpenAI-compatible 模型协议提供五个可审计分析工具，同时保证 SQL 只能以白名单只读查询执行。

**Architecture:** `src.agent.safety` 独立解析并限制 SQL；`src.agent.client` 将 LangChain `ChatOpenAI` 的消息与工具调用归一化；`src.agent.tools` 是唯一的工具注册和受控执行边界。LangChain 不创建数据库连接、不使用 SQL Agent；执行器以注入依赖实现 fake 测试与生产只读事务的分离。

**Tech Stack:** Python 3.13、LangChain Core、LangChain OpenAI、sqlglot、SQLAlchemy、Pydantic、pandas、pytest、Ruff。

---

## 文件职责

| 路径 | 职责 |
|---|---|
| `.env` | 本机私有 LLM 配置；始终被 Git 忽略。 |
| `.env.example` | 可提交的 LLM 配置模板，不包含真实密钥。 |
| `pyproject.toml` | 声明 LangChain 运行时依赖。 |
| `src/agent/__init__.py` | Agent 包边界。 |
| `src/agent/safety.py` | 单语句、只读、白名单、LIMIT 的 AST 校验。 |
| `src/agent/client.py` | LangChain 消息/工具调用适配器。 |
| `src/agent/tools.py` | 受控工具定义、只读 executor 与项目服务适配。 |
| `tests/agent/test_safety.py` | 安全边界回归测试。 |
| `tests/agent/test_client.py` | 无网络的 LangChain 客户端适配测试。 |
| `tests/agent/test_tools.py` | 工具注册、受控 SQL 与 ML/ROI 服务适配测试。 |
| `docs/learning/week-2.md` | Day 18 的学习记录与验证证据。 |

### Task 1: 配置模板、依赖与 Agent 包骨架

**Files:**
- Create: `.env.example`
- Create: `src/agent/__init__.py`
- Create: `tests/agent/__init__.py`
- Modify: `pyproject.toml:dependencies`
- Test: `tests/agent/test_client.py`

- [ ] **Step 1: 写失败测试，确认配置类型和客户端尚不存在**

```python
from src.agent.client import LLMResponse, ToolDefinition


def test_tool_definition_exposes_openai_function_schema():
    definition = ToolDefinition(
        name="get_metric_definition",
        description="读取指标口径",
        parameters={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    )
    assert definition.as_langchain_schema()["function"]["name"] == "get_metric_definition"
```

- [ ] **Step 2: 运行失败测试**

Run: `py -3.13 -m pytest tests/agent/test_client.py::test_tool_definition_exposes_openai_function_schema -v`

Expected: FAIL，原因是 `src.agent` 或 `ToolDefinition` 尚不存在。

- [ ] **Step 3: 创建不含密钥的配置模板和最小包骨架**

`.env.example` 内容：

```dotenv
# 填写任意 OpenAI-compatible 服务的地址、密钥和模型名；不要提交 .env。
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=
```

`.env` 使用相同字段但仅在用户本机创建，不执行 `git add`。将 `langchain-core>=0.3` 与 `langchain-openai>=0.3` 加入 `pyproject.toml` dependencies，并创建空的 `src/agent/__init__.py` 与 `tests/agent/__init__.py`。

- [ ] **Step 4: 安装项目依赖并确认运行时可导入**

Run: `py -3.13 -m pip install -e .`

Expected: `langchain_core` 与 `langchain_openai` 可导入，且 `.env` 仍由 `.gitignore` 忽略。

- [ ] **Step 5: 提交基础配置**

```powershell
git add pyproject.toml .env.example src/agent/__init__.py tests/agent/__init__.py
git commit -m "build: add LangChain agent runtime dependencies"
```

### Task 2: SQL AST 安全校验

**Files:**
- Create: `src/agent/safety.py`
- Test: `tests/agent/test_safety.py`

- [ ] **Step 1: 写失败测试，覆盖白名单、单语句与 LIMIT 边界**

```python
import pytest

from src.agent.safety import UnsafeQueryError, validate_read_only_sql


ALLOWED = {"marts.monthly_growth"}


def test_allowed_select_receives_default_limit():
    actual = validate_read_only_sql("select month_start from marts.monthly_growth", ALLOWED)
    assert "LIMIT 500" in actual.upper()


@pytest.mark.parametrize("sql", [
    "delete from marts.monthly_growth",
    "select * from raw.orders",
    "select 1; drop table warehouse.fact_orders",
    "select * from marts.monthly_growth limit 2001",
])
def test_unsafe_or_unbounded_sql_is_rejected(sql):
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql, ALLOWED)
```

- [ ] **Step 2: 运行失败测试**

Run: `py -3.13 -m pytest tests/agent/test_safety.py -v`

Expected: FAIL，原因是 `src.agent.safety` 尚不存在。

- [ ] **Step 3: 实现最小 AST 校验器**

实现 `UnsafeQueryError(ValueError)` 和：

```python
def validate_read_only_sql(sql: str, allowed_views: set[str]) -> str:
    expressions = sqlglot.parse(sql, read="postgres")
    if len(expressions) != 1 or not isinstance(expressions[0], exp.Select):
        raise UnsafeQueryError("only one read-only SELECT statement is allowed")
    for table in expressions[0].find_all(exp.Table):
        qualified_name = f"{table.db}.{table.name}" if table.db else table.name
        if qualified_name not in allowed_views:
            raise UnsafeQueryError("query references a non-governed view")
    limit = expressions[0].args.get("limit")
    if limit is None:
        expressions[0] = expressions[0].limit(500)
    elif int(limit.expression.name) > 2000:
        raise UnsafeQueryError("query limit exceeds 2000 rows")
    return expressions[0].sql(dialect="postgres")
```

将非数值 `LIMIT` 同样拒绝，避免转换异常泄露内部信息；保持异常信息不包含数据库 URL、API Key 或原 SQL 的敏感内容。

- [ ] **Step 4: 运行安全测试并检查格式**

Run: `py -3.13 -m pytest tests/agent/test_safety.py -v; py -3.13 -m ruff check src/agent/safety.py tests/agent/test_safety.py`

Expected: 全部 PASS；Ruff 无问题。

- [ ] **Step 5: 提交 SQL 防线**

```powershell
git add src/agent/safety.py tests/agent/test_safety.py
git commit -m "feat: add AST-guarded read-only SQL validation"
```

### Task 3: LangChain OpenAI-compatible 客户端

**Files:**
- Create: `src/agent/client.py`
- Test: `tests/agent/test_client.py`

- [ ] **Step 1: 写失败测试，使用 fake runnable 验证标准化响应**

```python
from src.agent.client import LangChainOpenAIClient, ToolDefinition


class FakeMessage:
    content = "我将查询月度商品金额。"
    tool_calls = [{"name": "run_safe_sql", "args": {"sql": "select 1"}, "id": "call_1"}]


class FakeRunnable:
    def invoke(self, messages):
        return FakeMessage()


def test_client_normalizes_langchain_tool_calls_without_network():
    client = LangChainOpenAIClient(runnable=FakeRunnable())
    result = client.complete([{"role": "user", "content": "查询"}], [ToolDefinition("run_safe_sql", "安全查询", {"type": "object"})])
    assert result.text == "我将查询月度商品金额。"
    assert result.tool_calls[0].name == "run_safe_sql"
    assert result.tool_calls[0].arguments == {"sql": "select 1"}
```

- [ ] **Step 2: 运行失败测试**

Run: `py -3.13 -m pytest tests/agent/test_client.py -v`

Expected: FAIL，原因是 `LangChainOpenAIClient` 尚不存在。

- [ ] **Step 3: 实现显式类型和可注入客户端**

定义冻结 dataclass：`ToolDefinition(name, description, parameters)`、`ToolCall(id, name, arguments)` 和 `LLMResponse(text, tool_calls, error=None)`。`ToolDefinition.as_langchain_schema()` 返回 `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`。`LangChainOpenAIClient.__init__` 无注入 runnable 时，以 `Settings` 的 `llm_base_url`、`llm_api_key`、`llm_model` 创建 `ChatOpenAI`；`complete` 将 dict 消息转为 LangChain message，使用 `bind_tools`，并规范化 `AIMessage.tool_calls`。空模型名或空密钥时返回 `LLMResponse(error="LLM is not configured")`，绝不发网络请求。

- [ ] **Step 4: 运行客户端测试**

Run: `py -3.13 -m pytest tests/agent/test_client.py -v; py -3.13 -m ruff check src/agent/client.py tests/agent/test_client.py`

Expected: 全部 PASS，且测试运行不访问网络。

- [ ] **Step 5: 提交模型适配器**

```powershell
git add src/agent/client.py tests/agent/test_client.py
git commit -m "feat: add LangChain compatible model client"
```

### Task 4: 受控工具注册与只读执行器

**Files:**
- Create: `src/agent/tools.py`
- Test: `tests/agent/test_tools.py`

- [ ] **Step 1: 写失败测试，先锁定 SQL 工具的执行边界**

```python
import pandas as pd

from src.agent.tools import AnalysisTools


class FakeExecutor:
    def __init__(self):
        self.sql = None

    def read_only_query(self, sql):
        self.sql = sql
        return pd.DataFrame([{"month_start": "2017-01-01", "item_revenue": 100.0}])


def test_safe_sql_uses_validated_query_and_returns_bounded_records():
    executor = FakeExecutor()
    tools = AnalysisTools(executor=executor, allowed_views={"marts.monthly_growth"})
    result = tools.run_safe_sql("select month_start, item_revenue from marts.monthly_growth")
    assert "LIMIT 500" in executor.sql.upper()
    assert result["rows"] == [{"month_start": "2017-01-01", "item_revenue": 100.0}]


def test_registered_tools_are_exactly_the_governed_five():
    tools = AnalysisTools(executor=FakeExecutor(), allowed_views={"marts.monthly_growth"})
    assert {tool.name for tool in tools.definitions()} == {
        "get_metric_definition", "run_safe_sql", "create_chart", "predict_repurchase", "simulate_campaign"
    }
```

- [ ] **Step 2: 运行失败测试**

Run: `py -3.13 -m pytest tests/agent/test_tools.py -v`

Expected: FAIL，原因是 `src.agent.tools` 尚不存在。

- [ ] **Step 3: 实现 executor 与 AnalysisTools**

定义 `ReadOnlyQueryExecutor` 协议的 `read_only_query(sql) -> pandas.DataFrame`。生产实现使用 SQLAlchemy `engine.begin()`，依次执行 `SET TRANSACTION READ ONLY`、`SET LOCAL statement_timeout = '5000ms'`，随后执行已验证 SQL；返回前限制至 2,000 行。`AnalysisTools.run_safe_sql` 必须先调用 `validate_read_only_sql`，再调用 executor，并返回 `{"sql": validated_sql, "rows": frame.head(2000).to_dict("records")}`。

其余工具保持无任意代码执行：`get_metric_definition` 调用 `src.analytics.metrics.get_metric_definition` 并序列化 dataclass；`create_chart` 只接受 `bar`、`line`、`scatter` 三种类型和受控 x/y 字段；`predict_repurchase` 调用现有安全特征和模型产物；`simulate_campaign` 调用 `src.ml.roi.simulate_roi`。`definitions()` 返回正好五个 `ToolDefinition`，没有内部 executor 或自由 SQL 字符串工具。

- [ ] **Step 4: 补齐预测、模拟和图表的失败/通过测试**

新增断言：未知图表类型被 `ValueError` 拒绝；`get_metric_definition("item_revenue")` 返回已治理的公式；模拟返回 `SimulationResult` 的序列化增量利润字段；预测函数只向模型传入 `FEATURE_COLUMNS`。运行：

```powershell
py -3.13 -m pytest tests/agent/test_tools.py -v
py -3.13 -m ruff check src/agent/tools.py tests/agent/test_tools.py
```

Expected: 全部 PASS，且写入 SQL、越权表和超过 2,000 行的请求均不能抵达 executor。

- [ ] **Step 5: 提交受控工具层**

```powershell
git add src/agent/tools.py tests/agent/test_tools.py
git commit -m "feat: add guarded LangChain analysis tools"
```

### Task 5: Day 18 集成验收与学习记录

**Files:**
- Modify: `docs/learning/week-2.md`
- Test: `tests/agent/test_safety.py`, `tests/agent/test_client.py`, `tests/agent/test_tools.py`

- [ ] **Step 1: 运行完整 Day 18 测试和静态检查**

```powershell
py -3.13 -m pytest tests/agent -v --basetemp "$env:TEMP\day18-agent"
py -3.13 -m ruff check src/agent tests/agent
```

Expected: 全部 PASS；日志中不出现 API Key；测试不访问网络。

- [ ] **Step 2: 进行配置安全检查**

Run: `git check-ignore -v .env; git ls-files .env .env.example; git diff --check`

Expected: `.env` 显示由 `.gitignore` 忽略；Git 仅追踪 `.env.example`；无空白错误。

- [ ] **Step 3: 记录 Day 18 学习笔记**

写入以下要点及实际验收命令输出：function calling 只是受控调用协议；AST 校验防止结构性越权；只读事务和超时是独立的纵深防线；为什么不用 LangChain SQL Agent；fake client 如何避免 CI 花费和网络依赖；真实 LLM 配置只放在 `.env`。

- [ ] **Step 4: 最终提交**

```powershell
git add docs/learning/week-2.md
git commit -m "docs: record Day 18 guarded agent learning"
git status --short
```

Expected: 仅允许 `.pytest-basetemp/` 等 Git 忽略或用户明确保留的本地临时文件存在；Day 18 源码、测试、模板和笔记全部已提交。
