# Day 19：可审计分析 Agent、评测与问数页面设计

## 目标与范围

Day 19 将 Day 18 的受控工具连接为可验证的自然语言分析 Agent：用户提问后，模型可在严格上限内选择已注册工具，系统记录每一步证据并输出结构化回答。本任务交付有界循环、离线黄金问题评测、命令行评测入口和 Streamlit AI 分析助手页面；不新增自由 SQL、写操作、第三方检索或自动部署。

## 方案与技术边界

采用方案 A：LangChain 只负责 OpenAI-compatible `ChatOpenAI`、消息对象和 `bind_tools` 协议；`AnalysisAgent` 自己控制循环、停止条件、参数验证、工具执行和审计。拒绝使用 LangChain `AgentExecutor`、SQL Agent 或 SQLDatabase，因为它们会隐藏循环行为并削弱 Day 18 的 AST、白名单和只读执行边界。

模型永远不直接访问数据库。它只能请求 Day 18 注册的五个工具；其中 SQL 工具继续经过 AST、函数白名单、只读事务、5 秒超时和 2,000 行限制。

## Agent 循环

`AnalysisAgent.run(question) -> AgentAnswer` 使用单一显式状态机。系统消息要求最终回答包含结论、证据、指标口径、时间范围和限制。每轮把当前消息和五个工具 schema 交给 `LangChainOpenAIClient`：

1. 若响应要求工具，逐个以 Pydantic schema 校验参数；只允许已注册名称。
2. 记录每个调用的名称、经脱敏后的参数、开始/结束时间、成功或结构化错误摘要；工具结果以 `ToolMessage` 回写到下一轮。
3. 工具参数错误、执行错误或未知名称不抛给用户，改为结构化工具错误供模型修正。
4. 最多运行 6 步；同一工具、同一规范化参数连续两次失败时立刻终止；超过步数时返回说明性安全失败。
5. 模型输出无工具调用的文本时，解析为最终回答；若必填审计字段缺失，系统补充“未提供”的显式限制，而不伪造事实。

`AgentAnswer` 包含 `answer`、`tool_trace`、`sql`、`metric_definition`、`data_range`、`limitations` 和可选 `chart`/`rows`。这使页面和评测都使用同一可审计对象。

## 黄金问题与离线评测

`configs/agent_questions.yml` 保存至少 30 个问题，覆盖增长、留存、客户、商品、履约、预测、营销模拟、不可回答和恶意 SQL。每条记录明确允许工具、期望数值或结果哈希/容差、是否应拒绝和评测模式；不把 API Key、真实用户数据或不稳定自然语言措辞写入 YAML。

`evaluate_agent` 默认使用 deterministic fake client 与 fake tools，不访问网络、不产生模型成本。它输出工具选择正确率、SQL 执行成功率、数值准确率、拒绝正确率、平均延迟和估算调用成本到 `artifacts/agent/evaluation.json`。真实模型评测必须显式传入 `--mode live`，并在 `.env` 完整配置时才允许运行。恶意 SQL 与越权问题的拒绝正确率必须为 100%。

## Streamlit 页面与演示降级

新增“AI 分析助手”页面，复用顶层导航与页面布局。实时模式仅在 `LLM_API_KEY` 和 `LLM_MODEL` 均存在时显示；用户提交问题后，页面显示回答、结果表、图表、SQL、指标口径、时间范围、限制及可折叠工具轨迹。

无 Key 或模型名时不调用网络，加载固定的演示问答和演示轨迹，并在页面顶部和结果区域明确标注“演示数据，非实时模型回答”。演示内容来自受控的项目指标和示例 SQL，不伪装为当前查询结果。

## 测试与验收

先为循环上限、工具白名单、连续失败停止、审计字段与 fake 评测写关键失败测试，再作最小实现。页面测试验证无配置时展示演示标识且不调用模型；评测测试验证假客户端输出完整 JSON，恶意 SQL 拒绝率为 100%。所有单元测试使用 fake client/tools，不依赖网络、API Key 或生产数据库。

验收命令：

```powershell
py -3.13 -m pytest tests/agent -v --basetemp "$env:TEMP\day19-agent"
py -3.13 scripts/evaluate_agent.py --mode fake
py -3.13 -m ruff check src/agent tests/agent app/pages scripts
```

Day 19 完成标准是：循环和停止条件可重复测试；工具轨迹可审计；黄金问题评测文件生成；未配置 API 时页面安全降级；真实模型调用仅由用户明确配置和实时提问触发。
