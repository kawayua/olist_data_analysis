# 数据字典 / Data Dictionary

## 读取约定 / Reading conventions

**中文。** 粒度描述一行代表什么；键描述唯一性或连接边界；来源列出上游对象。金额均为 Olist 源数据中的数值字段，未推导为利润。除另有说明外，行为型集市过滤 `delivered` 订单。`customer_id` 是订单地址记录，`customer_unique_id` 才用于跨订单客户统一。

**English.** Grain states what one row represents; key states the uniqueness or join boundary; source lists the upstream object. Monetary fields are numeric Olist source fields and are not converted into profit. Unless noted otherwise, behavioral marts filter to `delivered` orders. `customer_id` is an order-address record; `customer_unique_id` is used for cross-order customer identity.

## raw：原始 CSV 层 / raw: source CSV layer

| 对象 / Object | 粒度与键 / Grain and key | 来源 / Source | 关键字段 / Key fields |
| --- | --- | --- | --- |
| `raw.customers` | 一条客户地址记录；`customer_id` | `olist_customers_dataset.csv` | `customer_unique_id`, zip、city、state |
| `raw.orders` | 一笔订单；`order_id` | `olist_orders_dataset.csv` | `customer_id`, status、购买/批准/发货/送达/预计送达时间 |
| `raw.order_items` | 一笔订单中的一个商品行；(`order_id`, `order_item_id`) | `olist_order_items_dataset.csv` | `product_id`, `seller_id`, price、freight |
| `raw.payments` | 一笔订单中的一次支付序号；(`order_id`, `payment_sequential`) | `olist_order_payments_dataset.csv` | type、installments、`payment_value` |
| `raw.reviews` | 一条评价与订单的配对；(`review_id`, `order_id`) | `olist_order_reviews_dataset.csv` | score、评论文本、创建/答复时间 |
| `raw.products` | 一个商品；`product_id` | `olist_products_dataset.csv` | 葡语品类、文本长度、照片数、重量和尺寸 |
| `raw.sellers` | 一个卖家；`seller_id` | `olist_sellers_dataset.csv` | zip、city、state |
| `raw.geolocation` | 一条地理坐标记录；源文件无治理主键 | `olist_geolocation_dataset.csv` | zip、lat、lng、city、state |
| `raw.category_translation` | 一个葡语品类；`product_category_name` | `product_category_name_translation.csv` | 英文品类翻译 |

**中文。** raw 层保留文件字段并由导入契约检查九个文件的名称、主键和列。地理位置文件是完整输入边界的一部分，当前核心仓库事实表不以它生成空间维度。

**English.** The raw layer retains file fields and the ingestion contract checks the names, keys, and columns of all nine files. The geolocation file is part of the complete input boundary; current core warehouse facts do not use it to create a spatial dimension.

## staging：清洗层 / staging: typed cleanup layer

| 对象 / Object | 粒度与键 / Grain and key | 来源 / Source | 关键字段 / Key fields |
| --- | --- | --- | --- |
| `staging.orders` | 每订单一行；`order_id` | `raw.orders` | 规范状态、时间戳、`is_delivery_late`、时间异常标记 |
| `staging.order_items` | 每订单商品行；(`order_id`, `order_item_id`) | `raw.order_items` | `product_id`, `seller_id`, `price`, `freight_value` |
| `staging.payments` | 每订单支付序号；(`order_id`, `payment_sequential`) | `raw.payments` | payment type、installments、`payment_value` |
| `staging.products` | 每商品一行；`product_id` | products + category translation | 双语品类、属性、缺失品类/翻译标记 |
| `staging.sellers` | 每卖家一行；`seller_id` | `raw.sellers` | 补零 zip、小写 city、大写 state |
| `staging.reviews` | 每评价订单配对；(`review_id`, `order_id`) | `raw.reviews` | score、文本、规范时间戳 |

**中文。** staging 将字符串金额和时间转换为数值/时间类型，标准化地理文本，并显式暴露可疑状态—时间组合；它不把原始记录静默删除。

**English.** Staging converts string money and time fields to numeric/timestamp types, standardizes geographic text, and exposes suspicious status–timestamp combinations; it does not silently delete raw records.

## warehouse：可连接事实与维度 / warehouse: joinable facts and dimensions

| 对象 / Object | 粒度与键 / Grain and key | 来源 / Source | 关键字段 / Key fields |
| --- | --- | --- | --- |
| `warehouse.dim_customer` | 每真实客户一行；`customer_key`，`customer_unique_id` 唯一 | `raw.customers` | surrogate key、统一客户标识 |
| `warehouse.dim_product` | 每商品一行；`product_key`，`product_id` 唯一 | `staging.products` | 双语品类、商品属性、缺失标记 |
| `warehouse.dim_seller` | 每卖家一行；`seller_key`，`seller_id` 唯一 | `staging.sellers` | zip、city、state |
| `warehouse.dim_date` | 每日一行；`date_key` | `staging.orders` 日期范围 | 年、季、月、周、周末标记 |
| `warehouse.fact_orders` | 每订单一行；`order_id` | staging orders + 客户维度 + 订单级预聚合 | customer/date key、状态、时间、`item_revenue`、`freight_revenue`、`payment_value`、配送标记 |
| `warehouse.fact_order_items` | 每订单商品行；(`order_id`, `order_item_id`) | staging items + product/seller 维度 | 商品/卖家 key、price、freight |
| `warehouse.fact_payments` | 每订单支付序号；(`order_id`, `payment_sequential`) | staging payments | type、installments、value |
| `warehouse.fact_reviews` | 每评价订单配对；(`review_id`, `order_id`) | staging reviews | score、评论、时间 |

**中文。** `fact_orders` 先按订单分别汇总商品和支付，再连接，避免订单商品行与支付行直接相连造成多对多金额放大。金额口径由具体指标指定，不能把 `item_revenue` 与 `payment_value` 混加。

**English.** `fact_orders` aggregates items and payments separately by order before joining, preventing many-to-many money inflation from directly joining item and payment rows. Metric definitions choose a money basis; `item_revenue` and `payment_value` must not be added together.

## marts：分析集市 / marts: analysis marts

| 集市 / Mart | 粒度与键 / Grain and key | 来源 / Source | 关键字段 / Key fields |
| --- | --- | --- | --- |
| `monthly_growth` | 每自然月；`month_start` | delivered `fact_orders` + reviews | 商品/支付金额、订单/客户、新老客、AOV、环比、完整月标记 |
| `cohort_retention` | cohort 月 × 活动月；(`cohort_month`, `activity_month`) | delivered orders | cohort size、retained customers、rate、完整观察月 |
| `repurchase_horizons` | 首购品类 × 天数窗口；复合键 | delivered orders/items | 30/60/90 天资格客户、复购客户、比例 |
| `customer_360` | 每客户快照；`customer_key` | delivered orders/items/reviews | RFM、金额、配送、评分、segment、90 天资格与标签 |
| `customer_segment_strategy` | 每客户；`customer_key` | `customer_360` | segment、建议策略、客户/金额贡献 |
| `product_performance` | 每商品品类；`product_category` | orders/items/products/reviews/customer_360 | 订单/客户、商品/运费金额、延迟、评分、90 天复购 |
| `delivery_experience` | 每履约状态；`delivery_status` | delivered orders/reviews/customer_360 | late/on_time、配送天数、评分、90 天复购 |
| `delivery_order_analysis` | 每已送达订单；`order_id` | orders/reviews/customer_360 | 履约、评分、首购资格和复购标签 |
| `delivery_rating_analysis` | 履约状态 × 评分；复合键 | delivery order analysis | 评分计数与分布分析字段 |
| `state_performance` | 每客户州；`customer_state` | delivered orders + raw customers + reviews | 订单/客户、金额、延迟、配送、评分、90 天复购 |
| `state_monthly_performance` | 州 × 月；复合键 | state performance 来源 | 月度订单、客户、金额、履约与评分 |
| `customer_value_analysis` | 客户分群；`customer_segment` | customer_360 | 客户数、金额、贡献、策略字段 |
| `repurchase_behavior` | 首购品类 × 窗口；复合键 | delivered orders/items | 资格、复购、30/60/90 天比例 |
| `repurchase_intervals` | 复购间隔桶；`interval_bucket` | delivered orders | 0–30 至 181+ 天客户数 |
| `ml_customer_features` | 每客户；`customer_key` | 首笔已送达订单及其商品 | prediction time、六个首单特征、观察终点、资格、90 天标签 |

**中文。** 集市键是展示或分析前的安全聚合边界。跨集市连接必须再次检查粒度；例如品类行不能直接与支付行相连后求总金额。`eligible_for_90d = false` 或标签为 NULL 表示观察窗口未完整，不表示“不复购”。

**English.** Mart keys are safe aggregation boundaries before presentation or analysis. Any cross-mart join must re-check grain; for example, category rows must not be joined directly to payment rows before summing money. `eligible_for_90d = false` or a NULL label means the observation window is incomplete, not “did not repurchase.”
