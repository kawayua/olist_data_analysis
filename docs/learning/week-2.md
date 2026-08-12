# Week 2 补齐笔记：Day 8–10 指标治理、复购与客户策略

## Day 8：指标字典与月度增长集市

`configs/metrics.yml` 是项目的指标注册表。它将指标名称、中文标签、业务定义、公式、单位、粒度、过滤条件和分母规则放在版本控制中，避免 Dashboard、SQL 和报告对同一个指标各自解释。当前已登记 GMV、商品销售额、订单数、活跃客户、新客、老客、商品金额客单价、30/60/90 天复购率和延迟送达率。

`marts.monthly_growth` 的粒度为一行一个自然月，字段为：`month_start` (`date`), `item_revenue` (`numeric`), `payment_value` (`numeric`), `order_count` (`bigint`), `active_customers` (`bigint`), `new_customers` (`bigint`), `returning_customers` (`bigint`), `new_customer_item_revenue` (`numeric`), `returning_customer_item_revenue` (`numeric`), `item_revenue_aov` (`numeric`), `payment_aov` (`numeric`), `item_revenue_mom_pct` (`numeric`), `is_complete_month` (`boolean`)。它从已送达订单计算客户首次购买月，因此同一位客户在首购月计入新客、在之后仍有购买的月份计入老客；新客和老客是当月的客户类型，不是整个客户生命周期的永久标签。

月度集市使用完整的月份日历而不是只保留有订单的月份，因此 2016-11 这样的零交易月不会被悄悄省略。环比通过 `LAG` 读取上月商品金额；若上月为 0，环比应为 `NULL` 而不是无穷大。首月 2016-09 和末月 2018-08 不是完整自然月，`is_complete_month = false`，不能将这两个边界月的低金额直接解释为增长下降。

正式重建后共有 24 个月、96,478 笔已送达订单、13,221,498.11 商品金额、93,358 位客户和 1,836 个老客活跃月。小样本单元测试验证了第二个月有 1 位新客、1 位老客、2 笔订单，且客单价分母必须是订单数。

## Day 9：Cohort、右删失与 30/60/90 天复购

`marts.cohort_retention` 仍是一行一个 Cohort 月与活动月的组合；`src.analytics.retention.build_retention_matrix` 把没有回购活动的月份补成 0，确保热力图不会将“0 位回购”误显示成“缺少数据”。`wilson_interval` 用于二项比例的 Wilson 95% 置信区间；对于低复购率，它比只报告一个点估计更能显示抽样不确定性。

新增 `marts.repurchase_horizons`，粒度为一行一个复购观察窗口，字段为：`horizon_days` (`integer`), `eligible_customers` (`bigint`), `repurchased_customers` (`bigint`), `repurchase_rate_pct` (`numeric`), `ci_lower_pct` (`numeric`), `ci_upper_pct` (`numeric`)。观察资格按全局数据截止自然日判断，而后续订单是否落入窗口仍按精确 `purchased_at` 时间戳判断；这是为了与既有的 2018-08-29 观察截止日口径一致，同时不丢失同日稍晚发生的复购。

正式结果为：30 天 1,136 / 86,909 = 1.307%（95% CI 1.234%–1.385%）；60 天 1,372 / 81,265 = 1.688%（1.602%–1.779%）；90 天 1,514 / 75,387 = 2.008%（1.911%–2.111%）。窗口越长，具备完整观察期的客户越少；这是数据截止边界带来的资格变化，不是客户流失。

初版实现对每位客户和每个窗口执行相关子查询，构建超过合理时间。排查后将其改为先为每位客户聚合最早的后续购买时间，再与 30/60/90 天窗口比较。这个预聚合把重复扫描降为一次客户级连接，是 SQL 性能与粒度控制的又一个实例。

## Day 10：Customer 360 快照与客户策略表

`marts.customer_360` 增加 `feature_available_at` (`timestamp`) 字段。其值等于 `snapshot_at`，表示本行 RFM、金额、评价和配送特征在全局分析快照时才完整可用。该表用于客户分析与运营分群；它不应直接被当作“首购时点预测 90 天复购”的训练数据，因为其中包含首购之后才发生的行为。Day 14 将另建时间安全的机器学习特征集。

新增 `marts.customer_segment_strategy`，粒度为一行一个客户策略分群，字段为：`customer_segment` (`text`), `segment_definition` (`text`), `recommended_action` (`text`), `customer_count` (`bigint`), `customer_share_pct` (`numeric`), `item_revenue` (`numeric`), `item_revenue_share_pct` (`numeric`), `frequency_limitation` (`text`)。策略表将 RFM 规则、客户规模、收入贡献和建议放进可查询数据集，而不是散落在报告或未来页面代码里。

正式策略结果显示：`needs_attention` 为 23,079 位客户、贡献 41.289% 商品金额；`potential` 为 22,290 位、贡献 39.050%；两者合计占 48.597% 客户、贡献 80.339% 商品金额。`one_time_low_value` 客户最多（46,221 位，49.509%），但只贡献 16.472%。Frequency 的约 97% 值为 1，因此 F 使用 1 / 2 / 3+ 的稳定业务规则；不能把这一维度误解成有很细的频率差异。

## 本次验证

新增 Day 8–10 测试覆盖指标注册、月度新老客户核算、月度唯一性、Cohort 补零、Wilson 区间、30/60/90 复购结果、Customer 360 标签资格、策略覆盖和特征快照时间。下一步进入 Day 11：商品、履约与统计证据。
