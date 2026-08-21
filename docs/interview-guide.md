# 面试讲稿与追问 / Interview Guide

## 3 分钟叙述 / 3-minute narrative

**中文。** 我做的是一个可本地复现的 Olist 电商分析作品集。它从九个受契约约束的 CSV 开始，经过 raw、staging、warehouse、marts 四层；最关键的数据工程决定是把商品和支付分别在订单级预聚合，避免多商品、多支付订单在连接后重复计算金额，同时用 `customer_unique_id` 而不是地址层 `customer_id` 统一客户。仪表盘把增长、留存、客户价值、商品履约和 ROI 模拟放在同一口径上。结果显示延迟履约与更低评分强关联，但延迟与 90 天复购的差异在当前样本中 Fisher p=0.251，所以我没有把它写成因果流失。模型只用首单送达时已经可知的六个特征，严格隔离未来 90 天标签与最终测试；它提升了相对金额规则的最终测试排序，但绝对精度低，因此用于有限触达排序而不是自动决策。最后，我把 Agent 限制在 AST 校验的只读 SQL 和固定工具中，并把 30 例 fake 评估明确标为离线契约检查，不宣称真实 LLM 准确率。

**English.** I built a locally reproducible Olist e-commerce analytics portfolio. It starts with nine contract-governed CSVs and passes through raw, staging, warehouse, and marts. The key data-engineering decision is to preaggregate items and payments separately at order grain, preventing money double counting after joins for orders with multiple items and payments; customer identity is unified by `customer_unique_id`, not address-level `customer_id`. The dashboard puts growth, retention, customer value, product fulfillment, and ROI simulation on the same definitions. Results show a strong association between late delivery and lower ratings, but the difference in 90-day repurchase has Fisher p=0.251 in this sample, so I do not call it causal churn. The model uses only six features known when the first order is delivered and strictly isolates the future 90-day label and final test; it improves ranking over a money rule on final test but has low absolute precision, so it supports limited-outreach ranking rather than automatic decisions. Finally, I constrain the Agent to AST-validated read-only SQL and fixed tools, and label its 30-case fake evaluation as an offline contract check, not live-LLM accuracy.

## 10 分钟叙述 / 10-minute narrative

**中文。** 业务目标不是只报销售额，而是给出一条可审计的决策链：月度增长是新客、老客还是客单价变化；首购客户是否在完整观察期内复购；履约体验与评分和复购有何历史关联；以及有限触达预算怎样按概率排序。数据范围明确是 Olist 的匿名化历史快照，原始文件不提交。导入前检查九个 CSV 的文件名、主键和列；staging 把金额和时间字段转成类型，保留异常标记。仓库的订单事实分别聚合商品、运费和支付，且以真实客户键连接，从而把后续分析的双重计数风险前移解决。

分析集市将月份、cohort、客户 360、品类、履约、州和复购行为分成明确粒度。所有交易行为通常只看 delivered 订单；部分月和不完整 90 天窗口通过标记排除，不把“还没有观察够”误写成零。实际发现中，按时订单的评分分布明显更高；而按时与延迟首购的 90 天复购差为 -0.211 个百分点、置信区间跨零且 Fisher p=0.251，所以这是实验线索而非运营结论。`bed_bath_table` 的历史复购率高于 `health_beauty`，也只能作为分层探索起点。

ML 部分把预测时点固定为首单送达，标签是之后 90 天内是否有第二笔已送达订单；资格标记保证完整未来窗口。训练、选择、校准、最终测试按时间分割；选择主要看 PR-AUC，使用 Lift@10% 辅助，最终只报告一次。逻辑回归在最终测试的 PR-AUC 是 0.012274、Lift@10% 是 1.226994，优于金额规则的 0.009855 和 0.858896，但这在约 1% 正例下仍是很弱的绝对信号。ROI 页面把 uplift、成本、平均复购收入和预算作为显式情景；它不把自然发生的复购当成营销贡献。

Agent 是面向解释和受限查询的接口，不是数据库管理员。它的 SQL 必须是一条、来自白名单集市、只包含允许的分析函数，并在只读事务和五秒超时中执行；调用轨迹也会记录并脱敏。fake 评估使用确定性假 Agent，能离线检测工具选择、SQL 成功、数值和拒绝契约，却没有证明真实提供商的响应质量。下一步是在真正可控的环境里用小规模、明确预算的 live 样本验证 Agent，并以随机实验测量营销 uplift；同时补齐利润、触达和实验数据。

**English.** The business goal is not merely to report sales; it is to provide an auditable decision chain: whether monthly growth comes from new customers, returning customers, or AOV; whether first-purchase customers repurchase within a complete observation period; what historical association delivery experience has with ratings and repurchase; and how a limited outreach budget can be ranked by probability. The data scope is explicitly Olist's anonymized historical snapshot, and raw files are not committed. Ingestion checks the filenames, keys, and columns of nine CSVs; staging types money and timestamps while retaining anomaly flags. The warehouse order fact separately aggregates items, freight, and payments and joins on the real customer key, moving the double-counting risk upstream before analysis.

Analysis marts separate month, cohort, customer 360, category, fulfillment, state, and repurchase behavior into explicit grains. Transaction behavior normally uses delivered orders only; partial months and incomplete 90-day windows are flagged and excluded rather than recorded as zero. In the observed findings, on-time orders have a clearly higher rating distribution; the 90-day repurchase difference for on-time versus late first purchases is -0.211 percentage points, its interval crosses zero, and Fisher p=0.251, so it is an experiment lead rather than an operating conclusion. `bed_bath_table` has a higher historical repurchase rate than `health_beauty`, which is also only a starting point for stratified exploration.

For ML, prediction time is fixed at first-order delivery and the label is whether a second delivered order occurs in the next 90 days; the eligibility flag guarantees a complete future window. Training, selection, calibration, and final test are split by time; selection prioritizes PR-AUC with Lift@10% as an aid, and final test is reported once. Logistic regression has final-test PR-AUC 0.012274 and Lift@10% 1.226994, above the money rule's 0.009855 and 0.858896, but this remains a weak absolute signal at roughly 1% prevalence. The ROI page makes uplift, cost, average repurchase revenue, and budget explicit scenarios; it does not count naturally occurring repurchase as marketing contribution.

The Agent is an interface for explanation and constrained querying, not a database administrator. Its SQL must be one statement from allowlisted marts with permitted analytical functions, executed in a read-only transaction with a five-second timeout; call traces are also recorded and redacted. Fake evaluation uses a deterministic fake Agent, so it can test tool selection, SQL success, numeric, and rejection contracts offline but does not prove real-provider response quality. The next steps are a small, budgeted live sample in a controlled environment to validate the Agent, and randomized experiments to measure marketing uplift, alongside profit, contact, and experiment data.

## 技术追问与诚实回答 / Technical follow-ups and candid answers

1. **为什么不用 `customer_id` 算客户？ / Why not count customers with `customer_id`?**

   中文：它表示订单地址记录，同一真实客户可能有多个值；仓库以 `customer_unique_id` 生成唯一 `customer_key`。English: It represents an order-address record and one person may have multiple values; the warehouse generates a unique `customer_key` from `customer_unique_id`.

2. **如何避免金额重复？ / How is money double counting avoided?**

   中文：商品和支付先各自按订单聚合，再写入 `fact_orders`；不直接连接商品行与支付行后求和。English: Items and payments are aggregated separately by order before `fact_orders`; item rows and payment rows are not directly joined before summation.

3. **为什么分析限制为 delivered？ / Why restrict analysis to delivered?**

   中文：增长、履约和复购行为需要已完成交易的一致边界；这也意味着结果不代表取消订单或当前经营。English: Growth, fulfillment, and repurchase behavior need a consistent completed-transaction boundary; this also means results do not represent cancelled orders or current operations.

4. **90 天标签怎样防止右删失？ / How does the 90-day label prevent right censoring?**

   中文：只有观察终点至少晚于预测时点 90 天的客户进入分母和训练；其余标签为 NULL。English: Only customers whose observation end is at least 90 days after prediction time enter the denominator and training; the other labels are NULL.

5. **哪些特征被排除以防泄漏？ / Which features are excluded to prevent leakage?**

   中文：后续订单、评论、最终 RFM、最终累计消费和未来配送结果都排除，因为首单送达时不可见。English: Later orders, reviews, final RFM, final cumulative spend, and future delivery outcomes are excluded because they are unavailable when the first order is delivered.

6. **为什么优先 PR-AUC 而不是 Accuracy？ / Why prioritize PR-AUC over accuracy?**

   中文：正例约 1%，预测全为不复购也会有高 Accuracy；PR-AUC 更反映稀有正例的排序质量。English: Positives are about 1%, so predicting no repurchase for everyone would achieve high Accuracy; PR-AUC better reflects rare-positive ranking quality.

7. **为什么逻辑回归被选中？ / Why was logistic regression selected?**

   中文：在选择期它的 PR-AUC 最高，选择时未触碰最终测试；这不是说树模型普遍无效。English: It had the highest selection-period PR-AUC without touching final test; this does not say tree models are generally ineffective.

8. **模型能直接触发营销吗？ / Can the model directly trigger marketing?**

   中文：不能。它只给有限触达排序；低绝对精度、缺少 uplift/利润/成本真实结果，必须用实验决定策略。English: No. It only ranks limited outreach; low absolute precision and missing real uplift/profit/cost outcomes require experiments to decide policy.

9. **延迟导致低评分或低复购吗？ / Does lateness cause low ratings or repurchase?**

   中文：不能由本观察性数据得出。评分关联强，但复购差异不显著；两者都可能被品类、卖家和地区等混杂。English: This observational data cannot establish it. The rating association is strong but the repurchase difference is not significant; both can be confounded by category, seller, region, and other factors.

10. **Agent 如何防止危险 SQL？ / How does the Agent prevent dangerous SQL?**

   中文：SQLGlot AST 拒绝写入、DDL、多语句、未白名单表、非允许函数和非法 LIMIT；数据库执行器再设置只读事务和超时。English: A SQLGlot AST rejects writes, DDL, multiple statements, non-allowlisted tables, disallowed functions, and invalid LIMITs; the database executor then sets a read-only transaction and timeout.

11. **fake 评估的 100% 代表什么？ / What does 100% in fake evaluation mean?**

   中文：它只代表确定性 fake Agent 在这 30 个预设 golden cases 的工具/拒绝契约结果，绝不代表真实模型或真实 LLM 的 100% 准确率。English: It only represents deterministic fake-Agent tool/rejection contract results on these 30 predefined golden cases, never 100% accuracy for a real model or real LLM.

12. **下一项最有价值的数据是什么？ / What additional data would be most valuable?**

   中文：营销曝光、触达成本、毛利、实验分组和后续订单，可把排序和模拟升级为增量利润评估。English: Marketing exposure, contact cost, margin, experiment assignment, and subsequent orders would upgrade ranking and simulation into incremental-profit evaluation.
