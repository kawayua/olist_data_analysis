# 电商用户增长、留存与复购分析平台：项目中期报告

**报告日期：** 2026-08-12
**基线计划：** `docs/superpowers/plans/2026-08-09-ecommerce-analytics-platform-implementation.md`
**当前分支：** `master`，最新本地提交 `73d2153 feat: add customer 360 rfm mart`

> **进度更新（2026-08-12，Day 8–10 补齐并验收后）：** 原报告中 Task 6–8 的“部分完成”状态现已完成。新增了 `marts.monthly_growth`、指标字典、`marts.repurchase_horizons`（含 Wilson 95% 区间）、Cohort 补零矩阵、`feature_available_at` 与 `marts.customer_segment_strategy`。已通过 Navicat 直接查询三张新集市完成数据验收；26 项自动化测试和 Ruff 静态检查均通过。Task 9–17 的未开始状态不变；本报告下方表格保留的是补齐前的审计快照。

## 一、项目目标与当前判断

项目目标是在四周内完成一个以数据分析为主体、以机器学习为增强、以安全分析 Agent 为收尾的作品集：约 70% 数据分析、20% 机器学习、10% Agent。当前已完成“数据可复现、分析口径可信、客户与留存分析可复建”的基础阶段，处于原时间表的 Day 10 之后。

按日程，项目已完成前 10 个工作日，约为四周计划的一半；按 17 个原计划任务计算，Task 1–8 已完成，Task 9–17 尚未开始。因此，不能把项目表述为“完整应用已完成一半以上”；更准确的表述是：**数据工程、指标治理和核心客户分析已完成，完整 Dashboard、机器学习与 Agent 仍是后半程主工作量。**

## 二、原计划对照表

| 原任务 | 原计划内容 | 当前状态 | 已有证据 / 缺口 |
|---|---|---|---|
| Task 1（Day 1–2） | Python、Docker、PostgreSQL 可复现环境 | 已完成 | `pyproject.toml`、`.env.example`、`docker-compose.yml`、配置测试。 |
| Task 2（Day 3） | 数据清单、数据契约、可重复获取说明 | 已完成 | 9 张源表契约、`data/README.md`、`configs/datasets.yml`、契约测试。 |
| Task 3（Day 4） | Schema、数据库连接、导入批次审计 | 已完成 | `raw/staging/warehouse/marts/audit` 五层 schema、`audit.ingestion_runs`、数据库脚本与测试。 |
| Task 4（Day 5） | 原始数据导入和质量报告 | 已完成 | 可幂等 CSV 导入、质量检查与审计；原始表已加载。 |
| Task 5（Day 6–7） | staging、维度、事实表 | 已完成 | 星型模型、主外键、粒度测试；订单、商品、支付金额重复计算风险已验证并规避。 |
| Task 6（Day 8） | 指标字典和月度增长集市 | 已完成 | `configs/metrics.yml`、`src/analytics/metrics.py` 与 `marts.monthly_growth` 已实现；月度集市覆盖连续月份、新老客户、收入拆解、客单价、环比和边界月标志，并有小样本与 SQL 不变量测试。 |
| Task 7（Day 9） | Cohort 与 30/60/90 天复购分析 | 已完成 | `marts.cohort_retention`、`marts.repurchase_horizons`、观察期资格函数、Cohort 补零矩阵和 Wilson 95% 置信区间均已实现并受测；30/60/90 天结果已通过 Navicat 验收。 |
| Task 8（Day 10） | Customer 360、RFM、客户策略 | 已完成 | `marts.customer_360`、RFM Python 规则、90 天标签、`feature_available_at` 与 `marts.customer_segment_strategy` 已实现；策略表包含分群条件、客户数、收入贡献、行动建议和 Frequency 低变异限制。 |
| Task 9（Day 11） | 商品、履约、统计证据 | 未开始 | 缺产品表现/配送体验集市、统计模块与正式发现文档。 |
| Task 10（Day 12–13） | Streamlit Dashboard | 未开始 | 尚无 `app/`、数据访问仓库、图表组件和交互页面。 |
| Task 11（Day 14） | 时间安全机器学习数据集 | 未开始 | 尚无 `src/ml/`、ML 特征集市、时间切分与标签边界测试。 |
| Task 12（Day 15） | 业务基线与 Logistic Regression | 未开始 | 尚无模型训练、评估指标、模型对比产物。 |
| Task 13（Day 16） | 提升模型、校准、解释 | 未开始 | 尚无 LightGBM/替代模型、模型卡与可解释性报告。 |
| Task 14（Day 17） | 营销 ROI 模拟器与预测页 | 未开始 | 尚无模拟器和预测展示页。 |
| Task 15（Day 18） | OpenAI 兼容客户端与安全 SQL 工具 | 未开始 | 仅有配置中的 API 字段；无 Agent 模块、AST 校验与只读角色。 |
| Task 16（Day 19） | Agent 循环、评测集、问数页 | 未开始 | 无编排器、黄金问题集、评测报告、Agent 页面。 |
| Task 17（Day 20） | 端到端验收、部署、README、面试材料 | 未开始 | 尚无项目 README、架构/指标字典、部署和端到端验证脚本。 |

## 三、已交付成果

### 1. 可复现数据工程

数据从原始 CSV 到分析集市均有代码路径，而非依赖某次 Navicat 手工操作。`scripts/build_warehouse.py` 负责重建 staging 和 warehouse，`scripts/build_marts.py` 负责重建 Cohort 与 Customer 360。原始数据未提交到 Git，数据来源、文件名和字段契约已记录。

### 2. 可审计的数据模型

仓库将 `raw`、`staging`、`warehouse`、`marts` 分层；事实表有明确粒度：`fact_orders` 一行一订单，`fact_order_items` 一行一订单商品，`fact_payments` 一行一支付序号，`fact_reviews` 一行一评价订单关系。核心不变量测试保证订单粒度与商品金额总额在重建后保持正确。

### 3. 已验证的核心分析成果

- Cohort 留存集市：23 个首购月 Cohort，278 个 Cohort–活动月单元，明确标记不完整观察月份。
- 复购观察：完整 90 天窗口客户 75,387 位，其中 1,514 位复购，复购率 2.008%。
- Customer 360：一位有效客户一行，包含 RFM、服务体验特征、90 天资格/标签与可解释策略分群。
- RFM 结论：`potential` 与 `needs_attention` 合计贡献约 80.3% 商品金额，是后续运营实验优先候选群。

### 4. 工程质量

Day 10 合并前后已运行完整测试与静态检查：**19 项 pytest 测试全部通过，Ruff 无错误**。Customer 360 初版的相关子查询性能问题已定位并修复为客户粒度预聚合，重建测试约 2 秒完成；该过程已记录在学习笔记中。

## 四、当前风险与需要补齐的事项

1. **远程仓库未同步 master。** 本地 `master` 已含 Day 10 提交，但远程 `origin/feature/implementation` 停在 `cfed81a`。在展示或备份前，应将 `master` 推送到远程。
2. **还没有可视化入口。** 数据库和测试存在，不等于作品集能演示；Dashboard 是后半程最重要的可见交付。
3. **复购模型尚未开始。** 当前 RFM 是规则分群，不应写成“已完成机器学习预测”。
4. **Agent 尚未开始。** OpenAI 兼容 API 配置只是预留；安全 SQL、只读数据库角色与评测集必须先于真实 LLM 调用实现。
5. **指标治理仍不完整。** 月度增长集市与指标字典应在 Dashboard 前补齐，避免每个页面使用不同 SQL 口径。
6. **正式交付文档尚不完整。** 本报告和分析报告是中期材料；README、架构图、指标字典、模型卡、部署说明和面试指南仍待完成。

## 五、建议的后半程顺序

不要直接跳到 Agent。推荐按以下顺序推进：

1. 补齐 `monthly_growth` 和指标字典，统一收入、新客、复购、留存的定义。
2. 完成商品/履约集市与统计证据，先形成至少三条“现象—证据—限制—行动建议”的正式发现。
3. 用上述集市构建 Streamlit Dashboard，使已完成的分析能够被展示和讲解。
4. 建立严格时间切分的复购训练数据集与 Logistic Regression 基线，再比较提升模型；评价重点是 PR-AUC、Lift@K、校准，而非 Accuracy。
5. 将模型分数接到 ROI 模拟器，明确“增量转化率、客单价、毛利率、触达成本”都是可调整假设。
6. 最后实现受限 Agent：只读角色、白名单 marts、单条 `SELECT`、SQL AST 校验、工具调用轨迹和离线评测集。
7. 完成 README、部署、端到端验证和面试材料后，再作为完整作品集对外展示。

## 六、中期结论

项目已经跨过最容易被忽略、却最影响可信度的阶段：数据来源、粒度、金额聚合、观察期边界和可重复构建都已有明确约束与测试。下一阶段的关键不在于快速增加页面或调用大模型，而在于把现有可信分析转化为统一指标、可视化决策界面、时间安全模型和受控 Agent。这样最终展示的将不是“拼凑了很多技术”，而是一个可解释、可验证、可复现的完整分析产品。
