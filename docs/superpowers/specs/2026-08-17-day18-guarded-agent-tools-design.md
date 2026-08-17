# Day 18：兼容模型客户端与受控分析工具设计

## 目标与边界

本任务为后续自然语言分析 Agent 提供可测试、可审计且最小权限的基础设施。交付范围是模型协议适配、SQL 安全校验和五个受控工具；不实现 Agent 多轮循环、评测集或 Streamlit 问答页面，它们属于 Day 19。

系统必须允许用户将任意 OpenAI-compatible 服务的 URL、API Key 和模型名放入本地 `.env`，但单元测试不得读取真实密钥、不得发出网络请求，也不得需要可用的外部服务。

## 方案选择

候选方案包括：（一）模型直接生成 SQL 后连接数据库；（二）模型只能调用固定工具，SQL 另经 AST 与数据库双重限制；（三）不接模型，仅预设问题。选择方案二。方案一无法可靠限制提示注入或意外写入；方案三不具备通用问数能力。方案二把“模型建议”与“系统执行”分离，既可使用真实模型，也可在 CI 中由 fake client 完整验证。

## 配置与模型适配

本地新增 `.env`（不提交）与 `.env.example`（提交）。前者包含 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 的空白模板，用户自行填写真实值；后者以空值或无效示例说明字段。既有 `Settings` 继续作为唯一配置入口，密钥不写入日志、异常、测试快照或 Git。

`OpenAICompatibleClient` 接受 `Settings` 或等价配置，内部初始化官方 OpenAI Python SDK 的兼容客户端。对上提供稳定的 `complete(messages, tools) -> LLMResponse`：响应统一包含文本、规范化工具调用列表及结构化错误。内部 `ToolDefinition` 统一转换为 OpenAI function-tool JSON Schema。客户端构造不联网；只有 `complete` 被显式调用且配置齐全时才请求模型。测试注入 fake SDK/client，不调用真实 API。

## SQL 安全模型

`validate_read_only_sql(sql, allowed_views) -> str` 是数据库执行前的必经入口，使用 sqlglot 解析 AST，而非字符串关键字匹配。它要求：

- 输入只能解析为一条语句，拒绝分号拼接的第二条语句；
- 根节点必须为 `SELECT`（允许其只读查询结构），拒绝 DDL、DML、事务控制、命令和跨语句组合；
- AST 中每一张表必须完整匹配白名单的 `marts.*` 视图，拒绝 raw、staging、warehouse、未知表及无 schema 表；
- 无 `LIMIT` 时自动追加 `LIMIT 500`；大于 2,000 的限制值拒绝；
- 所有拒绝均抛出不泄露连接信息的 `UnsafeQueryError`。

AST 校验不能取代数据库权限。因此执行工具还会在连接上使用只读事务、`statement_timeout` 和 2,000 行上限。这是纵深防御：即使校验代码将来有缺陷，数据库仍不应允许写入。

## 工具边界

`AnalysisTools` 作为唯一注册表，暴露以下五个显式工具：`get_metric_definition`、`run_safe_sql`、`create_chart`、`predict_repurchase` 和 `simulate_campaign`。

- 指标工具只查询已有指标定义；
- SQL 工具仅执行经校验的白名单查询，并返回受行数限制的结构化结果与 SQL；
- 图表工具只接收已返回的数据和受控图形参数，不接受任意代码；
- 预测工具复用已保存模型及既有安全特征边界；
- 模拟工具复用 Day 17 的增量利润模拟器，不把自然复购收入误计为营销增量。

工具不拥有自由数据库连接创建能力。数据库执行通过注入的受控 executor，测试可替换为 fake executor；生产环境 executor 必须采用只读连接和超时设置。

## 测试与验收

先写失败测试，随后实现最小代码。安全测试覆盖允许的白名单查询、写入/DDL/多语句/越权表拒绝、默认限制和超限拒绝。工具测试覆盖白名单传递、只读执行设置、最大返回行数、结构化工具 schema，以及 fake client 下的协议响应转换。测试不得依赖网络、真实 API Key 或生产数据库。

Day 18 验收命令为：

```powershell
py -3.13 -m pytest tests/agent/test_safety.py tests/agent/test_tools.py -v
py -3.13 -m ruff check src/agent tests/agent
```

通过标准是：所有非只读或越权 SQL 均被拒绝，合法白名单 SQL 被安全限流，模型适配及五个工具都能在 fake 依赖下运行。Day 19 才允许模型根据这些工具做有界多轮调用并展示审计轨迹。
