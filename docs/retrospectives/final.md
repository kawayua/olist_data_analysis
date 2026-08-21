# 最终回顾 / Final Retrospective

## 已完成的业务学习 / Business learning completed

**中文。** 项目从“看销售”推进到可核查的增长、留存、履约和排序链路。已送达订单中，延迟组评分显著低于按时组：中位数 2 对 5，秩二列相关 -0.554。按时首购与延迟首购的 90 天复购率分别是 2.027% 与 1.816%，绝对差 -0.211 个百分点，Fisher p=0.251；因此它是需要分层实验的线索，而不是延迟造成复购损失的结论。`health_beauty` 和 `bed_bath_table` 的收入与复购表现也不一致，支持按品类做机制探索，而不是凭总体排名分配预算。

**English.** The project advances from “viewing sales” to a checkable chain for growth, retention, fulfillment, and ranking. Within delivered orders, the late group has materially lower ratings than the on-time group: medians 2 versus 5 and rank-biserial correlation -0.554. The 90-day repurchase rates for on-time and late first purchases are 2.027% and 1.816%, an absolute difference of -0.211 percentage points with Fisher p=0.251; this is a lead for stratified experiments, not a conclusion that lateness causes repurchase loss. `health_beauty` and `bed_bath_table` also show non-aligned revenue and repurchase patterns, supporting category-level mechanism exploration rather than assigning budget from an overall rank.

## 数据工程复盘 / Data-engineering retrospective

**中文。** 最大的工程风险是粒度。订单可有多个商品行和支付行，若直接连接再汇总，金额会系统性放大。解决方法不是靠仪表盘“修数”，而是在 `warehouse.fact_orders` 前分别做订单级商品/运费和支付预聚合。第二个风险是客户身份：`customer_id` 是地址层键，必须通过 `customer_unique_id` 建 `customer_key`。集市继续声明自己的键和粒度，使汇总、连接和展示都能复核。

**English.** The largest engineering risk is grain. An order can have multiple item rows and payment rows, so a direct join followed by aggregation systematically inflates money. The solution is not dashboard “correction,” but separate order-level item/freight and payment preaggregation before `warehouse.fact_orders`. The second risk is customer identity: `customer_id` is an address-level key and must become `customer_key` through `customer_unique_id`. Marts continue to declare their own keys and grains so aggregation, joins, and presentation can be reviewed.

## 泄漏控制与模型边界 / Leakage control and model boundaries

**中文。** 复购标签以首笔已送达订单的送达时间为预测时点，选择后续已送达订单，但以该后续已送达订单的 `purchased_at` 是否在未来 90 天窗口内作为正例条件，而不是其送达时间，并只保留完整观察窗口。未来订单、评论、最终 RFM 和最终累计消费没有进入首单预测特征。四段时间切分把训练、选择、校准和最终测试隔离，最终测试只报告一次。选中的真实模型是逻辑回归，而不是演示占位：最终测试 PR-AUC 0.012274、Lift@10% 1.226994，优于首单金额规则的 0.009855 和 0.858896；但正例率约 1%、绝对信号较弱，不能把概率当成确定会复购，也不能把排序改进当成营销因果增量。

**English.** The repurchase label fixes prediction time at first-delivered-order delivery, selects a later delivered order, and marks a positive when that later delivered order's `purchased_at` is within the future 90-day window, rather than using its delivery time; it keeps only complete observation windows. Future orders, reviews, final RFM, and final cumulative spend do not enter first-order prediction features. The four-way temporal split isolates training, selection, calibration, and final test, with final test reported once. The selected real model is logistic regression, not a placeholder: its final-test PR-AUC is 0.012274 and Lift@10% is 1.226994, above the first-order-item-revenue rule's 0.009855 and 0.858896; however, prevalence is about 1% and absolute signal is weak, so probability is not certain repurchase and ranking improvement is not causal marketing incrementality.

## Agent 安全与评估边界 / Agent safety and evaluation boundaries

**中文。** Agent 只访问白名单分析集市和固定工具。AST 校验拒绝写入、DDL、多语句、未治理来源、非分析函数和非法行数限制；执行层还采用只读事务、超时和最多 2,000 行，审计记录会脱敏敏感参数。`evaluation.json` 的 30 个例子使用确定性 fake Agent，因而可以离线验证工具路由、SQL、数值和拒绝契约；它不是、也不应被描述为真实模型或提供商的准确率。真实模型提供商曾表现出配置/可用性不稳定的风险，所以 live 评估必须显式确认、配置密钥、限制在最多 5 例和明确的时延/估计成本预算内。

**English.** The Agent accesses only allowlisted analysis marts and fixed tools. AST validation rejects writes, DDL, multiple statements, non-governed sources, non-analytical functions, and invalid row limits; execution additionally uses a read-only transaction, timeout, and at most 2,000 rows, while audit records redact sensitive arguments. The 30 cases in `evaluation.json` use a deterministic fake Agent, so they can validate tool routing, SQL, numeric, and rejection contracts offline; they are not, and must not be described as, accuracy for a real model or provider. Real model providers have shown configuration/availability instability risk, so live evaluation requires explicit confirmation, configured credentials, and caps of five cases with defined latency and estimated-cost budgets.

## 复现与下一步 / Reproducibility and next steps

**中文。** 默认验收使用 `py -3.13 scripts/verify_project.py`；完整验收使用 `py -3.13 scripts/verify_project.py --full`。二者都不调用真实 LLM，默认流程也不下载 CSV、重建表或训练模型。需要恢复数据时，按 `data/README.md` 取得九个 CSV，再执行 bootstrap、导入、warehouse、marts、训练和 fake 评估的顺序。下一步应补充营销曝光、成本、利润和随机实验数据，按品类/州/卖家分层验证履约干预，并在受预算约束的 live 样本上评估 Agent；这些步骤才可能把关联和模拟推进为可信的增量决策证据。

**English.** Default acceptance uses `py -3.13 scripts/verify_project.py`; complete acceptance uses `py -3.13 scripts/verify_project.py --full`. Neither calls a live LLM, and the default path also does not download CSVs, rebuild tables, or train a model. To restore data, obtain the nine CSVs according to `data/README.md`, then run bootstrap, ingestion, warehouse, marts, training, and fake evaluation in order. Next, add marketing exposure, cost, margin, and randomized-experiment data; validate fulfillment interventions by category/state/seller strata; and evaluate the Agent on a budget-bounded live sample. Only those steps can advance associations and simulation toward credible incremental decision evidence.
