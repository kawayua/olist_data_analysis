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

## Day 11：Mann–Whitney U 与统计证据的起点

对两组人工构造且完全分离的连续数据 `group 0 = [1, 2, 3, 4]`、`group 1 = [10, 11, 12, 13]`，双侧 Mann–Whitney U 检验得到 `p = 0.028571...`。在预先设定的显著性水平 `alpha = 0.05` 下，这意味着：若两组实际来自相同分布，观察到当前或更极端排序差异的概率低于 5%，因此可拒绝“无分布位置差异”的原假设。

这只是对构造样本和统计函数正确性的验证，并不构成 Olist 业务结论，也不表示某个因素导致了复购或满意度变化。p 值只反映证据强弱，不表达差异大小；下一步需要补充秩二列相关（rank-biserial correlation）等效应量，并在真实集市数据上同时报告样本量、差异、区间和混杂因素限制。

### 商品与履约集市的粒度控制

`marts.product_performance` 的粒度是一行一个商品品类，统计已送达订单数、客户数、品类商品金额、品类运费、运费率、延迟配送率，以及只在客户首个已送达订单且具有完整 90 天观察期时计算的复购率。商品金额和运费来自 `fact_order_items` 的订单内预聚合；支付明细没有与商品明细直接连接，因此避免了一笔多商品、多支付订单产生金额倍增。

`marts.delivery_experience` 的粒度是一行一个履约状态（`on_time` 或 `late`），提供订单与客户规模、配送时长、相对预计送达日期的偏差、平均评分和同口径复购率。它表达的是履约体验与结果的描述性关联；商家、品类、地区和时间等混杂因素尚未控制，不能据此说“延迟配送导致复购下降”。

### 订单粒度履约分析与真实评分检验

`marts.delivery_order_analysis` 是一行一个已送达订单的分析集市。评分先在 `fact_reviews` 内按订单聚合，再与订单相连，因此多个评价关系不会增加订单样本。`delivery_status` 由受治理的 `is_delivery_late` 派生；复购资格和标签仅在客户首个已送达订单上保留，避免把客户级 90 天标签重复附在后续订单上。

对非空评分订单执行双侧 Mann–Whitney U：按时组 88,171 笔，中位数评分 5；延迟组 7,661 笔，中位数评分 2。延迟减按时的中位数差为 -3 分（-60.0%，确定性 bootstrap 95% CI [-3, -3]），秩二列相关为 -0.554，说明延迟组整体评分明显更低。SciPy 双精度 p 值显示为 0 是数值下溢，不是概率恰好为 0；应报告为 `p < 5 × 10^-324`。此结论是强关联证据，仍不是因果结论。

### 两比例复购比较

对完整观察期内的首购客户，按时首购组为 68,778 人，90 天复购 1,394 人（2.027%）；延迟首购组为 6,609 人，复购 120 人（1.816%）。延迟减按时的绝对差是 -0.211 个百分点，相对差 -10.4%，比例差 95% 区间为 [-0.550, 0.128] 个百分点；双侧 Fisher 精确检验 `p = 0.251`。由于区间跨越 0 且 p 大于 0.05，当前样本不能拒绝两组总体复购率相同的原假设。这个“不显著”不是证明不存在影响，而是说明该低复购率比较的证据仍不够确定。

## Day 12–13：Dashboard 数据粒度、页面级筛选与业务叙事

Dashboard 的筛选器必须和查询数据集市的粒度一致。月度增长集市支持月份范围和不完整月份开关，因此增长诊断页只展示这些条件；Cohort 集市支持首购月和观察完整性，因此留存复购页只展示 Cohort 条件；商品页的品类条件只影响品类表现，不能假装同时过滤州履约或延迟评分。没有有效筛选维度的客户价值页直接说明其为统一快照下的全局 RFM 结果。这样可以防止页面出现“控件已选择、数据其实未变”的误导。

比例在州粒度汇总时不能直接相加。延迟率的正确分子是每州 `订单数 × 延迟率`，分母是总订单数；90 天复购率的正确分子是已复购首购客户数，分母是具有完整 90 天观察期的首购客户数。金额、订单数和客户数可以求和，但比率必须按原始分母加权。

本阶段新增 `customer_value_analysis`、`repurchase_behavior`、`repurchase_intervals` 和 `delivery_rating_analysis`。前两者分别支持 RFM 分群及按首购品类的 30/60/90 天复购率；二购间隔桶互斥；“首购/二购/多购”仅描述可观测订单频次，不直接称为流失。配送延迟与评分是强关联线索，不能替代控制品类、卖家、区域和时间混杂因素后的因果分析。

视觉编码也必须服从问题：GMV、订单和购买用户量纲不同，P1 采用三张上下排列趋势图；P2 用购买用户、购买频次和客单价展示可观测增长驱动，而非伪造精确归因瀑布图；气泡图明确规定 X、Y 和面积各自对应的真实指标。

## Day 16：四段时间隔离、候选选模与概率校准

复购模型按 `prediction_time` 严格划分为训练、选择、校准和最终测试四段：训练段内部再留出最后 10% 只用于 LightGBM 早停；选择段用 PR-AUC 为主、Lift@10% 为并列判据比较候选；校准段只拟合已选模型的 sigmoid 校准器；最终测试段在模型和校准器都确定后只评估一次。这样可以避免最终测试信息通过拟合、早停、调参、选模或校准回流。实际 82,500 个样本的总体 90 天复购率仅 1.095%，Accuracy 即使把客户全部判为不复购也会显得很高，无法衡量少数正例的发现质量；PR-AUC 聚焦正类的精确率与召回率权衡，Lift@10% 则直接回答触达最高分 10% 客户时相对随机触达富集了多少复购客户。

选择期最终选中 `logistic_regression`，其 PR-AUC 为 0.014919、Lift@10% 为 1.321780。sigmoid 校准只改变概率尺度，不改变排序，也不能借校准结果重新选模；本次校准期 PR-AUC 与 Lift@10% 前后保持 0.021741 和 1.630676，而 Brier score 从 0.240971 降至 0.011727。Brier score 是预测概率与实际 0/1 标签之间平方误差的均值，越低表示概率越接近实际结果；首单金额只是原始排序分数，不是概率，因此其 Brier score 保持 `null`。

一次性最终测试中，校准后的逻辑回归 PR-AUC 为 0.012274，高于首单金额规则的 0.009855；Lift@10% 为 1.226994，高于基线的 0.858896；模型 Brier score 为 0.009785。结果说明当前模型相对简单规则有小幅排序提升且概率误差较低，但绝对 PR-AUC 仍很低，受到约 1.1% 稀疏标签、仅六个首单时点特征、历史时间窗口和潜在分布漂移限制。特征重要性只描述模型在当前数据中的关联贡献，不证明配送时长、金额或其他特征会因果地改变复购；业务干预仍需随机实验或更严格的因果设计验证。

## Day 17：增量利润、预算约束与因果边界

营销 ROI 模拟只把“触达后相对不触达多出的复购”计为营销效果，因此增量复购数用高分客户的预测概率之和乘以假设提升率计算，再换算增量收入、营销成本和净增量利润。自然复购本来就可能发生；如果把这部分总收入也算作营销收益，会系统性高估活动回报。

利润最大化与 ROI 最大化不是同一目标。小预算方案可能因分母较小而得到更高 ROI，但只创造较少的绝对增量利润；在预算、单次触达成本和最大触达比例约束下，默认建议应优先选择净增量利润最高的可执行方案，ROI 只作为资金效率的辅助视角。

模型给出的是复购关联概率，不是“发放营销触达会造成多少复购”的因果效果。保守、基准和乐观 uplift 都是待验证的业务假设；需要在可比人群中随机分配触达组与对照组，用 A/B 测试估计增量复购与不确定性，再用实验结果更新模拟参数。

## Day 18：为自然语言分析 Agent 建立“能用但不能越权”的工具边界

Day 18 的目标不是立即做出一个会多轮对话的 Agent，而是先解决一个更基础的问题：将来模型即使把 SQL 或工具参数生成错了，系统怎样仍能阻止它越权访问、写入数据库、泄露密钥，或一次返回过大的结果。Day 19 才会把模型、工具调用循环、审计记录和问答页面串起来；本日只交付一个可单独测试的安全地基。这个拆分很重要，因为“模型会不会说得通”和“系统会不会安全执行”是两种不同能力，后者不能交给提示词来保证。

### 为什么采用 LangChain 混合结构，而不直接让模型连接数据库

本项目使用 `langchain-core` 与 `langchain-openai` 对接 OpenAI-compatible 模型服务。`LangChainOpenAIClient` 读取统一的 `Settings`，在真正调用时构造 `ChatOpenAI`，并将项目自己的 `ToolDefinition` 转为 LangChain function schema；模型返回的文本和工具调用再被标准化为 `LLMResponse(text, tool_calls, error)`。这样做的好处是：以后更换模型服务只需调整配置，Day 19 的 Agent 也能沿用成熟的消息和工具调用协议。

但 LangChain 只负责“模型如何提出工具调用”，绝不负责“模型可以执行什么”。没有使用 LangChain SQL Agent、SQL Database 或自动 SQL 执行链，因为它们会让模型得到过宽的查询能力，也会把 mart 白名单、行数限制和项目的审计边界藏在框架内部。实际结构是：模型提出请求 → `AnalysisTools` 接收一个明确工具名和 JSON 参数 → 项目安全层验证 → 受控执行器执行 → 结构化结果回给上层。模型永远没有数据库连接对象，也不能自行决定执行器。

### 配置、密钥与“测试不联网”原则

本地 `.env` 用于保存 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`；`.gitignore` 已忽略 `.env`，因此真实 Key 不会被纳入 Git。提交到仓库的 `.env.example` 只保留可复现的字段和空值模板，使用者复制为 `.env` 后自行填写。数据库已有的开发连接字段也保留在示例中，但生产中仍应改用独立的最小权限只读账号。

客户端构造本身不联网。只有 `complete(...)` 在 API Key 和模型名都存在时才会尝试请求服务；如果未配置，它返回固定的 `LLM is not configured` 错误，而不是创建客户端或发送请求。测试通过注入 fake runnable：它模拟 `invoke` 的模型响应和 `bind_tools` 的绑定结果，所以测试既不需要 API Key，也不产生网络流量或调用成本。外部服务异常、畸形工具历史或无法解析的模型响应统一变为 `LLM request failed`，不把连接串、密钥或原始异常透传到页面。

一个容易忽略的细节是多轮工具调用的关联。助手消息中的每个调用都保存 `id`、`name` 和 `args`，后续 `ToolMessage` 用同一个 `tool_call_id` 关联结果。若调用参数不是结构化字典，客户端直接安全失败。这样 Day 19 在保存会话历史时能知道“这份工具结果对应哪一次调用”，而不是把上一轮的结果错误地配给下一轮。

### SQL 的第一道防线：解析 AST，而不是搜索危险关键词

`validate_read_only_sql(sql, allowed_views)` 是所有 SQL 执行前的必经入口。它用 `sqlglot` 将 PostgreSQL SQL 解析为抽象语法树（AST），再检查节点类型；这比查找 `delete`、`drop` 等字符串可靠得多。例如关键字可以出现在注释、字符串或复杂嵌套结构中，简单黑名单很容易漏掉真正的写入语句，也容易误伤合法查询。

校验规则包括：只能有一条语句，根节点只能是 `SELECT` 或只读集合运算（如 `UNION ALL`）；任何 DML、DDL、命令和事务节点都拒绝；`SELECT INTO` 和 `FOR UPDATE` 也拒绝，因为前者会创建对象、后者会加锁。每一个真实表都必须完整写成白名单中的 `marts.视图名`，不能访问 `raw`、`staging`、`warehouse`、未知 marts、无 schema 表或跨 catalog 表。CTE 是例外：同一条查询内部定义的 CTE 别名不是数据库表，因此允许在后续查询中引用；但 CTE 内部的真实表仍会被逐一验证，不能借 CTE 隐藏 `raw.orders` 或 `DELETE ... RETURNING`。

行数限制也在 AST 的所有层级检查：没有外层限制时系统自动加 `LIMIT 500`；任何 `LIMIT` 必须是正整数，且不能超过 2,000。特别测试了两种常见绕过方式：在 CTE 内写 `LIMIT 2001`，以及在 `UNION ALL` 的某一个子查询内写超限 `LIMIT`。两种都会被拒绝，而不是只检查最外层的 `LIMIT`。这解释了“安全校验要递归遍历整棵语法树”的原因：攻击和误用往往发生在嵌套层，不在最外层。

被拒绝时只抛出不含原 SQL、连接串或凭据的 `UnsafeQueryError`。例如测试故意在注释中放入 PostgreSQL URL，错误文本也不含这段内容。安全报错应告诉用户“越权查询不允许”，但不应把可被利用的数据库信息带到日志或模型上下文。

### SQL 的第二道防线：数据库只读事务与超时

即使 AST 校验正确，也不能只依赖应用层，因此 `SQLAlchemyReadOnlyExecutor` 是第二道独立边界。它在短事务内依次执行 `SET TRANSACTION READ ONLY` 和 `SET LOCAL statement_timeout = '5000ms'`，再执行已经验证过的查询，并在 DataFrame 返回前再次截断为最多 2,000 行。前两条设置分别防止事务写入和防止慢查询长时间占用数据库；最后的 DataFrame 截断则避免下游序列化、图表或模型上下文接收过大的结果。

真正的生产防线还应包含数据库账号权限：应用使用的 Agent 账号仅授予所需 marts 的 `SELECT`，不授予 raw/staging/warehouse、建表或写入权限。代码中的只读事务是纵深防御，不是替代数据库权限；如果未来有人错误修改了应用校验，最小权限账号仍能阻断实际写操作。

### 五个受控工具及各自的输入输出边界

`AnalysisTools` 是 Day 18 唯一的工具注册表，准确暴露五个工具：`get_metric_definition`、`run_safe_sql`、`create_chart`、`predict_repurchase` 和 `simulate_campaign`。工具数量和 schema 都有测试，避免 Day 19 接入时意外多出未审查的能力。

- `get_metric_definition` 只读取已有的指标契约，保证 Agent 回答 GMV、订单数或复购率时先使用项目统一口径，而不是临时编造公式。
- `run_safe_sql` 先执行 AST 校验，只有通过后才调用注入的只读 executor，并以 ISO 日期、普通数值和 `null` 的 JSON 安全格式返回不超过 2,000 行的记录。非法 SQL 在到达 executor 前就会被拒绝。
- `create_chart` 只接受 `bar`、`line`、`scatter` 三种图形和显式 `data/x/y` 字段，不接收 Python、JavaScript 或任意图表表达式；数据最多 2,000 行，并要求 x、y 确实存在于传入字段中。
- `predict_repurchase` 只把 Day 14–16 定义的六个首购时点特征传给已保存并校准的模型。即使请求中混入 `repurchased_within_90d` 等标签字段，也不会传进模型，从接口层继续维护防标签泄漏的训练边界；返回值必须落在 0 到 1 的概率区间。
- `simulate_campaign` 复用 Day 17 的增量利润模拟器。它只接受显式预算、触达成本、客单收入、概率、情景和最大触达比例，输入情景必须恰好是 `name` 与有限数值 `uplift_rate`；概率和情景数组均限 2,000 项，结果序列化为可审计的增量收入、成本、净增量利润与 ROI，而不是把自然复购收入误当成营销收益。

这里“JSON 边界”同样是一种工程安全性：DataFrame 可能含 `Timestamp`、`date`、带时区 `datetime`、`Decimal`、`NaN`、`NaT` 等 Python 对象，不能直接交给模型或网页。工具将它们统一序列化为 ISO 时间、数字和 JSON `null`，保证 API 边界稳定，也防止页面在正确查询后因序列化失败而崩溃。

### 本日验证与得到的结论

Day 18 的测试刻意不依赖真实数据库或模型。测试覆盖了合法白名单 SELECT 自动补限制、集合查询、嵌套/CTE 限制、DML/DDL/多语句/越权表/无 schema/锁语句拒绝、错误脱敏、只读事务与 5 秒超时、2,000 行截断、日期和 Decimal 的 JSON 序列化、五工具 schema、图表与营销输入上限、特征白名单，以及 fake LangChain 客户端的工具绑定、消息关联和安全失败行为。

最终复验使用 `py -3.13 -m pytest tests/agent -v --basetemp "$env:TEMP\\day18-final"`、`py -3.13 -m ruff check src/agent tests/agent`、`git check-ignore -v .env`、`git ls-files .env .env.example` 和 `git diff --check`。这些命令分别验证功能、安全边界、风格、真实 `.env` 不会入库、示例配置的受控提交状态以及补丁没有空白错误。通过它们只说明 Day 18 的“模型与工具边界”满足预期；它不代表模型已经具备可靠业务推理能力，也不代表营销模拟的 uplift 已被因果实验验证。下一步 Day 19 要在这些限制之上实现有上限的工具调用循环、请求/工具审计轨迹、评测问题集和 Streamlit 问答体验。

## Day 19：可审计分析 Agent、黄金问题集与安全问答页面

### 这一日究竟解决什么问题

Day 18 已保证“某一次工具调用不会越权”，但一个可以自然语言问数的 Agent 还必须解决第二层问题：模型可能连续调用工具、参数可能不合法、工具可能失败、模型也可能在拿到结果后给出没有证据的结论。Day 19 因此不是把模型直接接到页面上，而是实现一个明确的、有停止条件的状态机 `AnalysisAgent`，让每个问题都走同一条可回放路径：用户问题 → 模型提出工具调用 → 参数校验与受控执行 → 工具结果回传模型 → 最终回答，同时保留每一步轨迹。

采用的是“LangChain 协议 + 项目自定义循环”的结构。LangChain 仍负责 OpenAI-compatible `ChatOpenAI`、消息格式、`bind_tools` 和模型返回的 tool call 协议；`AnalysisAgent` 自己控制循环次数、可用工具、失败停止和证据收集。没有采用黑箱 `AgentExecutor`，原因不是它不能工作，而是它会把何时停止、为何调用某工具、失败后做了什么隐藏在框架内部。对于数据分析作品集，显式状态机更容易解释、测试和审计。

### 有界循环如何工作

每一次 `run(question)` 都先写入系统提示和用户问题，然后只把 Day 18 注册的五个工具定义交给客户端。模型若不要求工具，系统直接把它的文本作为回答；模型若要求工具，则系统先检查工具名是否仍在当前注册表中，再用 Pydantic 严格校验参数。参数模型使用 `extra="forbid"` 和严格类型，因此模型多传字段、把对象错误写成字符串或调用未知工具，都不会进入业务执行器。

成功调用会产生 `ToolTrace`：其中包括调用 ID、工具名、经过脱敏和长度截断的参数、成功状态、耗时和结果摘要。结果再作为关联同一 `tool_call_id` 的 `tool` 消息回传模型，模型才能基于真实工具结果组织最终结论。`AgentAnswer` 不只保存回答文本，还保存 SQL、指标口径、数据范围、行数据、图表、限制与整段轨迹；页面不需要重新猜测模型做过什么。这解决了传统聊天机器人“给出一个数字，却无法说明口径、查询和时间范围”的问题。

循环最多允许六次工具调用，而不是无限重试。若同一规范化的“工具名 + 参数”连续失败两次，系统立即返回安全失败；若已达到步数上限，也返回“分析未在允许步数内完成”的限制说明。这样可以避免模型在错误 SQL、无效参数或不可能完成的问题上不断消耗 API 调用。工具内部异常只以 `tool_execution_failed` 这样的安全摘要进入轨迹，不把连接信息、堆栈或密钥回传给模型或页面。

审计日志也需要防泄漏。参数键名含 `api_key`、`authorization`、`password`、`secret` 或 `token` 时会写成 `[REDACTED]`；长文本、长数组和对象均有长度及条目上限。`run_safe_sql` 是唯一在轨迹中保留 SQL 的工具，因为 SQL 本身是业务证据且已经过 AST 安全检查；其他可疑 SQL 字段会被遮蔽。这说明“可审计”不等于“把所有输入原样记录”。

### 为什么需要黄金问题集，而不能只看几个演示问答

真实 Agent 的回答往往语言流畅，即使它选错数据集、没有调用工具或错误地执行越权 SQL，也可能看起来合理。因此项目把期望行为写成版本控制中的 `configs/agent_questions.yml`：共 30 个唯一案例，覆盖增长、留存、客户、商品、履约、预测、营销模拟、不可回答和恶意 SQL 九类场景。每条案例明确问题、预期工具序列、是否应得到成功 SQL、可选的期望数值和是否必须拒绝。

评测器 `evaluate_agent` 对每个问题调用一次 Agent，并输出 UTF-8 JSON 报告。它衡量工具选择准确率、预期 SQL 成功率、数值准确率、拒绝准确率、平均延迟和估算成本。这里的“数值准确”只针对明确给出数值期望的题目，采用相对/绝对容差比较；其余问题不会被错误计入分母。拒绝题目检查回答或限制说明是否含“不能、拒绝、不允许、只读、无法执行”等明确安全信号。它不是在证明模型普遍聪明，而是在防止改动后悄悄破坏一组重要、可重复的行为契约。

`py -3.13 scripts/evaluate_agent.py --mode fake` 使用确定性的 fake agent，而不是连接外部模型或数据库。它用于验证评测格式、指标计算和拒绝案例，也不会产生 API 成本；本次产物 `artifacts/agent/evaluation.json` 覆盖全部 30 题，工具选择、预期 SQL、带数值期望问题和拒绝问题的准确率均为 1.0，平均延迟与估算成本为 0。这个 100% 只代表 fake 基准按人工预设行为工作，**不能**写成真实 LLM 在 30 题上达到 100%；接入真实模型后，需要另行运行 live 评测并记录模型、提示词、时间和费用。

### Streamlit 页面：演示模式与实时模式的边界

新增页面 `app/pages/7_AI分析助手.py` 并加入顶部导航。它复用现有 Dashboard 主题和导航，展示分析回答、结果表、图表、受控 SQL、指标口径、数据范围、限制和可折叠工具轨迹。界面中的 SQL 与轨迹不是为了让用户自行绕过控制，而是让业务读者能够核对“这个结论基于什么”。

页面只有在 `LLM_API_KEY` 和 `LLM_MODEL` 都非空时才会构造 `LangChainOpenAIClient` 与真实 `AnalysisAgent`；单独填 URL 或只填 Key 都不会发送网络请求。未配置时，页面展示固定的 `build_demo_answer()`，标题、回答和提示均明确标注“演示数据，非实时模型回答”。演示对象包含三个月的虚构商品金额、示例 SQL 和示例轨迹，目的是让评审能检查页面结构，不应被用于业务决策。这个降级设计既让无密钥环境可展示，又不会把演示值伪装成实时查询结果。

### 本日复现与检查重点

Day 19 应至少执行：

```powershell
py -3.13 -m pytest tests/agent tests/visualization -v --basetemp "$env:TEMP\day19-final"
py -3.13 scripts/evaluate_agent.py --mode fake
py -3.13 -m ruff check src/agent tests/agent app/pages scripts
git check-ignore -v .env
git diff --check
```

第一条验证 Agent 状态机、评测逻辑、页面演示与既有可视化没有回归；第二条生成可审阅的离线评测产物；Ruff 检查风格；`git check-ignore -v .env` 确认真实密钥文件继续被忽略；最后一条检查补丁没有空白问题。真正使用时先复制 `.env.example` 为 `.env`，填写 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`，再启动 Streamlit；若准备 live 评测，还应先确定预算、超时、模型版本和结果记录方式。

Day 19 的交付说明“Agent 能在严格边界内调用工具并留下证据”，不说明自然语言回答天然正确，更不说明预测概率或营销 uplift 具有因果含义。下一阶段应进一步做部署/体验收口，并把真实模型的黄金集结果、失败案例和人工复核流程纳入最终项目报告。

### 真实运行复盘：为什么“哪个州的销售额最好”会耗尽六步

在配置真实模型后，问题“这些月里哪一个州的销售额最好？”首次没有得到业务结论，而是返回“分析未在允许步数内完成”。这条提示不是数据库连接失败，也不是 API Key 无效；它是 `AnalysisAgent` 在已经执行满六次工具调用、模型仍未输出最终文本时给出的安全停止结果。六步上限仍然是正确的保护，防止模型在错误路径上无限消耗调用次数；真正需要修复的是模型为什么没有得到可行动的反馈。

页面轨迹给出了诊断证据：四次 `run_safe_sql` 均是 `tool_execution_failed`，另两次 `get_metric_definition` 分别请求了不存在的 `sales` 与 `sales_by_state`。项目真实的受控指标名是 `item_revenue`（商品销售额），而州维度结果位于 `marts.state_performance`，对应字段是 `customer_state` 与 `item_revenue`。模型并不知道这些命名，便用日常语言中的 sales 进行猜测；更严重的是，原循环把 `KeyError`、`UnsafeQueryError` 和数据库工具异常全部折叠成同一个通用错误码。这样做避免了泄露连接信息和原始 SQL，却没有告诉模型“这是指标名不存在”还是“这条 SQL 被安全策略拒绝”，模型只能继续盲试，最后耗尽步数。

这次问题体现了 Agent 设计中的一个重要平衡：**安全报错不能泄露内部细节，但必须足够可修正。**修复后，指标找不到时工具结果给模型 `metric_not_found`；SQL 违反受控边界时给 `query_rejected`；其他内部执行故障仍保持 `tool_execution_failed`。这些是稳定的、无敏感信息的机器可读错误码，模型可据此调整下一次调用，但看不到原 SQL、数据库 URL、堆栈或密钥。

同时，系统提示增加了最小的业务导航，而不是开放任意数据库能力：列出合法指标名，并明确说明“州销售额使用 `marts.state_performance` 的 `customer_state` 和 `item_revenue`；得到一次有效受控查询结果后直接作答，不要重复相同调用”。这样模型面对本题应优先形成类似 `SELECT customer_state, item_revenue FROM marts.state_performance ORDER BY item_revenue DESC LIMIT 1` 的单条白名单查询；SQL 仍会经过 Day 18 的 AST、函数白名单、只读事务、超时和行数限制。

修复采用 TDD。先写一个 scripted fake client：它依次请求无效指标 `sales` 和被安全层拒绝的 SQL，断言回传的工具消息分别含 `metric_not_found`、`query_rejected`，且不含原始私密拒绝文本；运行后测试如预期失败，因为旧代码只产生 `tool_execution_failed`。随后只在编排层增加 `KeyError` 与 `UnsafeQueryError` 的安全映射和受控提示；修复后 `tests/agent/test_orchestrator.py` 的 15 项测试通过，Ruff 与 `git diff --check` 通过。这个过程说明：遇到真实模型失败时，先利用可折叠轨迹定位“模型请求了什么、哪个工具失败”，再写可重复的回归测试，而不是直接把最大步数从 6 调大。增加步数只会提高成本，不能解决信息不足或工具契约不清的问题。

## Day 20：本地交付验收记录 / Local delivery acceptance record

**中文（2026-08-21，复验）。** Day20 不调用真实 LLM，且没有手动启动 Docker/Docker Compose、下载源 CSV、启动 Streamlit、训练或加载模型；验证器仍会运行非启动性的 `docker info`。质量入口成功读取现有数据库并写入已忽略质量报告；默认 `verify_project.py` 已通过，但 `--full` 因完整 pytest 失败而失败。直接入口旧错误实际发生在 Docker 可用性检查之后的数据库就绪观测，不是依赖检查前。将 `TEMP`/`TMP` 仅对测试进程指向新的、仓库内已忽略目录后，精确全量 pytest 终态为 216 通过、9 失败（225 项，125.64 秒）：1 项是尚未补写的 Day20 准确性断言，8 项通过测试调用 `build_marts.py` 后因现有 `marts.customer_360` 的 `DuplicateTable` 失败；未额外运行重建命令。Ruff 通过。还须如实记录 TDD 偏差：原始两个短语断言没有红灯，之后才增加标题断言取得红灯。

**English (2026-08-21, rerun).** Day20 does not call a real LLM, and did not manually start Docker/Docker Compose, download source CSVs, start Streamlit, train, or load a model; the verifier does run non-starting `docker info`. The quality entrypoint successfully read the existing database and wrote its ignored report; default `verify_project.py` passed, while `--full` failed because full pytest failed. The former direct-entry error actually occurred during database readiness after the Docker availability check, not before dependency checks. With `TEMP`/`TMP` process-locally set to a new ignored repository directory, exact full pytest completed with 216 passed and 9 failed (225 tests, 125.64 seconds): one was the not-yet-written Day20 accuracy assertion, and eight invoked `build_marts.py` through test code then failed `DuplicateTable` on existing `marts.customer_360`; no additional rebuild command was run. Ruff passed. The TDD deviation is also explicit: the original two-phrase assertion did not go RED; the heading assertion was added afterwards to obtain RED.
