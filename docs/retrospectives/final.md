# 最终回顾 / Final Retrospective

## 已完成的业务学习 / Business learning completed

**中文。** 项目从“看销售”推进到可核查的增长、留存、履约和排序链路。已送达订单中，延迟组评分显著低于按时组：中位数 2 对 5，秩二列相关 -0.554。按时首购与延迟首购的 90 天复购率分别是 2.027% 与 1.816%，绝对差 -0.211 个百分点，Fisher p=0.251；因此它是需要分层实验的线索，而不是延迟造成复购损失的结论。`health_beauty` 和 `bed_bath_table` 的收入与复购表现也不一致，支持按品类做机制探索，而不是凭总体排名分配预算。

**English.** The project advances from “viewing sales” to a checkable chain for growth, retention, fulfillment, and ranking. Within delivered orders, the late group has materially lower ratings than the on-time group: medians 2 versus 5 and rank-biserial correlation -0.554. The 90-day repurchase rates for on-time and late first purchases are 2.027% and 1.816%, an absolute difference of -0.211 percentage points with Fisher p=0.251; this is a lead for stratified experiments, not a conclusion that lateness causes repurchase loss. `health_beauty` and `bed_bath_table` also show non-aligned revenue and repurchase patterns, supporting category-level mechanism exploration rather than assigning budget from an overall rank.

**口径说明 / Definition note.** 这些客户、商品和履约发现使用 purchase-anchored 集市标签：首购 `purchased_at` 起算 90 天，观察完整性截至 delivered 数据的 `MAX(purchased_at)`。它不是 ML 的首单送达时间标签。 / These customer, product, and delivery findings use purchase-anchored mart labels: 90 days from first-purchase `purchased_at`, with completeness assessed through delivered-data `MAX(purchased_at)`. This is not the ML first-delivery-time label.

## 数据工程复盘 / Data-engineering retrospective

**中文。** 最大的工程风险是粒度。订单可有多个商品行和支付行，若直接连接再汇总，金额会系统性放大。解决方法是在 `warehouse.fact_orders` 前分别做订单级商品/运费和支付预聚合。第二个风险是客户身份：`customer_id` 是地址层键，必须通过 `customer_unique_id` 建 `customer_key`。集市继续声明自己的键和粒度，使汇总、连接和展示都能复核。

**English.** The largest engineering risk is grain. An order can have multiple item rows and payment rows, so a direct join followed by aggregation systematically inflates money. The solution is separate order-level item/freight and payment preaggregation before `warehouse.fact_orders`. The second risk is customer identity: `customer_id` is an address-level key and must become `customer_key` through `customer_unique_id`. Marts declare their own keys and grains so aggregation, joins, and presentation remain reviewable.

## 泄漏控制与模型边界 / Leakage control and model boundaries

**中文。** 本节只描述 ML 的 delivery-anchored 标签，不替代分析集市口径。ML 以首笔已送达订单的送达时间为预测时点，选择后续已送达订单，但以该后续订单的 `purchased_at` 是否在未来 90 天窗口内作为正例条件，而不是其送达时间，并只保留完整观察窗口。未来订单、评论、最终 RFM 和最终累计消费没有进入首单预测特征。四段时间切分隔离训练、选择、校准和最终测试。选中的逻辑回归最终测试 PR-AUC 为 0.012274、Lift@10% 为 1.226994，优于首单金额规则的 0.009855 和 0.858896；但正例率约 1%、绝对信号较弱，不能把排序改进当成营销因果增量。

**English.** This section describes only the delivery-anchored ML label; it does not replace the analysis-mart definition. ML fixes prediction time at first-delivered-order delivery, selects a later delivered order, and marks a positive when that later order's `purchased_at` is within the future 90-day window, rather than using its delivery time; it keeps only complete observation windows. Future orders, reviews, final RFM, and final cumulative spend do not enter first-order prediction features. The four-way temporal split isolates training, selection, calibration, and final test. Logistic regression reaches final-test PR-AUC 0.012274 and Lift@10% 1.226994, above the first-order-item-revenue rule's 0.009855 and 0.858896; prevalence is about 1%, so this weak absolute signal is not causal marketing incrementality.

## Agent 安全与评估边界 / Agent safety and evaluation boundaries

**中文。** Agent 只访问白名单分析集市和固定工具。AST 校验拒绝写入、DDL、多语句、未治理来源、非分析函数和非法行数限制；执行层还采用只读事务、超时和最多 2,000 行，审计记录会脱敏敏感参数。`evaluation.json` 的 30 个例子使用确定性 fake Agent，只验证离线工具路由、SQL、数值和拒绝契约，不代表真实模型或提供商准确率。live 评估必须显式确认，并受到例数、时延和估计成本预算约束。

**English.** The Agent accesses only allowlisted analysis marts and fixed tools. AST validation rejects writes, DDL, multiple statements, non-governed sources, non-analytical functions, and invalid row limits; execution additionally uses a read-only transaction, timeout, and at most 2,000 rows, while audit records redact sensitive arguments. The 30 cases in `evaluation.json` use a deterministic fake Agent and validate only offline tool-routing, SQL, numeric, and rejection contracts, not real-model or provider accuracy. Live evaluation requires explicit confirmation and bounded case, latency, and estimated-cost budgets.

## 复现与下一步 / Reproducibility and next steps

**中文。** 默认验收使用 `py -3.13 scripts/verify_project.py`；扩展验收使用 `py -3.13 scripts/verify_project.py --full`，它只运行明确列出的非 SQL 测试目录与 Ruff，排除会重建当前数据库的 `tests/sql`。二者都不调用真实 LLM，也不下载 CSV、重建表或训练模型。需要恢复数据时，按 `data/README.md` 取得九个 CSV，再执行 bootstrap、导入、warehouse、marts、质量检查、训练和 fake 评估的顺序。四个运行时产物采用 `artifacts/manifest.json` 记录的 `generated-after-clone` 策略。

**English.** Default acceptance uses `py -3.13 scripts/verify_project.py`; extended acceptance uses `py -3.13 scripts/verify_project.py --full`, which runs only explicitly listed non-SQL test directories plus Ruff and excludes the current-database-rebuilding `tests/sql`. Neither path calls a live LLM, downloads CSVs, rebuilds tables, or trains a model. To restore data, obtain the nine CSVs according to `data/README.md`, then run bootstrap, ingestion, warehouse, marts, quality checks, training, and fake evaluation in order. The four runtime artifacts follow the `generated-after-clone` policy recorded in `artifacts/manifest.json`.

`py -3.13 scripts/run_quality_checks.py` 读取现有数据库 / reads the existing database，并且只写入 / and writes only `artifacts/quality/latest.json`；它不重建数据层 / it does not rebuild a data layer.

## Day 20 验收记录 / Day 20 acceptance record

**中文（2026-08-21，最终审查修订）。** 默认与扩展验收均**不调用真实** LLM。早期验收曾让 `--full` 运行无边界 pytest，因而把 `tests/sql` 中会调用建表入口的测试带到当前数据库；这些旧结果不能证明非破坏性交付。最终修订把 `--full` 限定到 `tests/agent`、`tests/analytics`、`tests/ingestion`、`tests/integration`、`tests/ml`、`tests/validation` 和 `tests/visualization`，保留 600 秒有限超时，再运行 Ruff。最终修复只执行聚焦的 verifier/end-to-end 回归测试、Ruff 和 diff 检查，不执行 SQL 测试、Docker/数据库写操作、制品生成、模型训练或真实 LLM。RED/GREEN 的精确结果与提交记录见 `final-fix-report.md`。

**English (2026-08-21, final-review correction).** Default and extended acceptance **do not call a real** LLM. Earlier acceptance let `--full` run unbounded-scope pytest, which brought `tests/sql` tests that call build entrypoints into the current database; those historical results do not prove non-destructive delivery. The final correction limits `--full` to `tests/agent`, `tests/analytics`, `tests/ingestion`, `tests/integration`, `tests/ml`, `tests/validation`, and `tests/visualization`, retains a finite 600-second timeout, and then runs Ruff. The final repair runs only focused verifier/end-to-end regression tests, Ruff, and a diff check—never SQL tests, Docker/database writes, artifact generation, model training, or a live LLM. Exact RED/GREEN results and the commit are recorded in `final-fix-report.md`.
