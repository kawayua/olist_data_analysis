# 指标字典 / Metric Dictionary

## 总则 / General rules

**中文。** 以下指标来自受治理 SQL 或 `configs/metrics.yml` 对应的项目口径。除明确说明外，订单口径过滤 `order_status = 'delivered'`；百分比乘以 100；分母为零时返回 NULL 而不是伪造 0。所有金额均为货币字段的历史数值，非利润、非当前财务报表。

**English.** The metrics below come from governed SQL or the corresponding project definitions in `configs/metrics.yml`. Unless explicitly stated, order-based metrics filter `order_status = 'delivered'`; percentages are multiplied by 100; a zero denominator returns NULL rather than a fabricated zero. All money is historical numeric source data, not profit or a current financial statement.

| 指标 / Metric | 公式 / Formula | 过滤、分母与粒度 / Filter, denominator, and grain | 注意事项 / Caveat |
| --- | --- | --- | --- |
| **GMV / 支付总额** | `SUM(payment_value)` | 已送达订单；订单级或汇总维度；无比例分母 | 本项目将 GMV 作为支付金额口径；不与商品金额相加，也不等同利润。 / In this project GMV uses payment value; it is not added to item revenue and is not profit. |
| **商品金额 / Item revenue** | `SUM(item_revenue)`，其中订单商品先汇总 `SUM(price)` | 已送达订单；订单、月、州或其他集市维度；无比例分母 | 用于商品层交易价值；运费单列，避免与支付或商品行的多对多连接重复计数。 / It is product-level transaction value; freight is separate, and preaggregation avoids double counting from many-to-many joins. |
| **订单数 / Order count** | `COUNT(DISTINCT order_id)` | 已送达订单；当前集市维度 | 同一订单有多个商品或支付时仍只计一单。 / An order with multiple items or payments still counts once. |
| **客户数 / Customer count** | `COUNT(DISTINCT customer_key)` | 已送达订单；当前集市维度 | `customer_key` 由 `customer_unique_id` 统一，不以地址层 `customer_id` 计真实客户。 / `customer_key` unifies `customer_unique_id`, rather than counting address-level `customer_id` as a real customer. |
| **延迟率 / Delayed-delivery rate** | `AVG(is_delivery_late::integer) × 100` | 已送达且具有可比较送达/预计送达时间的订单；分母为可计算延迟标记的订单 | 延迟定义为实际送达晚于预计送达；缺失时间不能被解释为按时。 / Late means actual delivery after estimated delivery; missing timestamps are not interpreted as on-time. |
| **平均评分 / Average rating** | `AVG(average_review_score)`，订单内多评价先取平均 | 已送达、当前维度且有评分的订单；分母为有可用评分的订单 | 评论是自选择观察，评分关联不是因果效应。 / Reviews are self-selected observations; rating associations are not causal effects. |
| **90 天复购率 / 90-day repurchase rate** | `repurchased_first_purchase_customers / eligible_first_purchase_customers × 100`；标签选择后续已送达订单，但以该后续已送达订单的 `purchased_at` 是否在首笔送达后的 `(prediction_time, prediction_time + 90 days]` 判定，不以其送达时间判定。 / The label selects a later delivered order, but tests whether that later delivered order's `purchased_at` is in `(prediction_time, prediction_time + 90 days]` after first delivery, not its delivery time. | 分母为首购客户且 `eligible_for_90d = true`；可按品类、履约状态、州或总体汇总 | 只有完整观察窗口客户进入分母；未满 90 天不等于未复购。分子和分母对应集市中的 `repurchased_*_customers` 与 `eligible_*_customers`。 / The denominator includes only first-purchase customers with `eligible_for_90d = true`; fewer than 90 observed days does not mean no repurchase. The numerator and denominator correspond to the mart's `repurchased_*_customers` and `eligible_*_customers`. |

## 衍生指标 / Derived metrics

**中文。** 商品客单价为 `SUM(item_revenue) / COUNT(DISTINCT order_id)`；支付客单价为 `SUM(payment_value) / COUNT(DISTINCT order_id)`。月环比为 `(本月值 / 上月值 - 1) × 100`，上月为零或不存在时为 NULL。复购 cohort 的留存率为某 cohort 在活动月再次购买的去重客户数除以该 cohort 首购客户数；仅标记为完整观察月的格子适合比较。RFM 的 Recency、Frequency、Monetary 是快照描述和分层工具，不能作为首购即时预测的特征。

**English.** Item-revenue AOV is `SUM(item_revenue) / COUNT(DISTINCT order_id)`; payment AOV is `SUM(payment_value) / COUNT(DISTINCT order_id)`. Month-over-month growth is `(current month / prior month - 1) × 100` and is NULL when the prior month is zero or absent. Cohort retention is distinct customers from a cohort who purchase again in an activity month divided by the cohort's first-purchase customer count; only cells marked as complete observation months are comparable. RFM Recency, Frequency, and Monetary are snapshot descriptions and segmentation tools, not features available for immediate first-order prediction.

## 指标解释边界 / Interpretation boundaries

**中文。** 延迟组与按时组评分或复购率的差异是观察性比较，可能受品类、地区、卖家、季节、订单价值和未观测服务因素混杂。ROI 模拟中的 uplift 是显式假设，不是从这些指标推导出的营销因果增量。展示时应同时给出时间范围、过滤条件和可观察分母。

**English.** Differences in ratings or repurchase rates between late and on-time groups are observational comparisons and may be confounded by category, region, seller, season, order value, and unobserved service factors. The uplift in ROI simulation is an explicit assumption, not a causal marketing increment derived from these metrics. Presentations should state the time range, filters, and observable denominator together.
