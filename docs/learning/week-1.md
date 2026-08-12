# 第 1 周学习笔记

## Day 1-2：可复现的开发环境

### 为什么需要虚拟环境

`.venv` 为本项目隔离 Python 依赖。项目通过 `pyproject.toml` 说明所需库，其他人不需要猜测应该安装哪些包，也不会因系统 Python 中已有的版本而得到不同结果。

### 为什么用 Docker 运行 PostgreSQL

数据库是分析项目的重要依赖。`docker-compose.yml` 把 PostgreSQL 版本、账号、数据库名、端口、持久卷和健康检查都写成可执行配置。这样开发机、演示机和未来部署环境会使用相同的数据库服务。

### 环境变量解决什么问题

`.env.example` 只提供变量名和本地开发默认值；真实的 API Key 或密码写入未提交的 `.env`。这种做法避免密钥进入 Git 历史，同时让应用可以在不同环境使用不同配置。

### 第一个测试在验证什么

`tests/test_config.py` 验证 `Settings` 会正确拼接 PostgreSQL 连接字符串。它先在 `src.config` 不存在时失败，再在最小实现后通过。这说明测试不是“事后装饰”，而是先定义我们希望配置模块提供的行为。

### 本次遇到的环境问题

Docker Desktop 重启后没有自动启动时，`docker` 客户端会提示找不到 `dockerDesktopLinuxEngine` 命名管道。确认 Docker Desktop 进程不存在后，启动 `D:\DockerDesktop\Docker Desktop.exe` 即恢复 Engine；无需重建容器或修改数据库配置。

### 本日验收命令

```powershell
.\.venv\Scripts\python -m pytest tests/test_config.py -v
.\.venv\Scripts\python -m ruff check src tests
docker compose ps
docker compose exec -T db pg_isready -U analytics -d olist
```

### 复盘问题

1. 虚拟环境和 Docker 容器分别隔离什么？
2. 为什么 `.env` 需要被 Git 忽略，但 `.env.example` 要提交？
3. 为什么不能只看 Docker Desktop 图标，而要检查 `pg_isready`？
4. 如果配置写死在代码里，部署到另一台电脑会发生什么？

## Day 3：数据契约与数据血缘

数据契约把每份 CSV 的文件名、字段顺序和主键显式写进代码。它回答的是“这份外部数据应当长什么样”，而不是“程序能否勉强读进来”。当上游文件改名、删列或改变字段拼写时，契约会在导入前发现问题。`geolocation` 没有源主键，因为同一邮编前缀在原始数据中允许出现多次；不应为了方便而强行声明一个错误主键。

## Day 4：数据库分层、事务与审计

PostgreSQL 的 Schema 是数据库内的逻辑命名空间：`raw` 保留原始事实，`staging` 做清洗，`warehouse` 建模，`marts` 提供指标，`audit` 记录运行过程。把 SQL 放入可重复执行的初始化文件，意味着新环境可以用同一命令建出相同结构。`audit.ingestion_runs` 不存业务分析结果，而是存每次导入的时间、状态、文件和行数；它让“数据从哪来、何时失败”有据可查。

## Day 5：幂等导入与数据质量

CSV 行数正确不等于数据正确：它可能少列、主键重复、订单项找不到订单，或出现不合理的负金额。导入器先校验结构，再计算 SHA-256 文件哈希；相同内容已成功导入时直接跳过。这种“重复运行不产生重复结果”的性质称为幂等性。质量报告会把行数、主键问题和业务规则异常保存为 JSON，后续每次刷新数据都可以比较变化。

### 本次真实数据发现

1. 九张 Olist 源表全部导入；最大的 `geolocation` 表有 1,000,163 行。它没有源主键是数据集的既有特性，不应把重复邮编前缀误判成错误。
2. 所有已声明主键均没有重复或空值；`order_items` 到 `orders` 的外键检查发现 0 条孤儿记录。
3. 负商品金额、负支付金额、未知订单状态，以及“交付早于下单”的记录均为 0。这些结果只说明本次规则未发现异常，不代表数据天然完美；后续仍要检查缺失、业务口径和跨表粒度。

## Day 6：粒度与 staging 设计

在 Navicat 中确认 `raw.orders` 的八个字段均为 `text`，因此不能直接依赖数据库做日期计算。`raw.orders` 有 99,441 行，且 `COUNT(order_id)` 与 `COUNT(DISTINCT order_id)` 均为 99,441，所以它的粒度是一行一笔订单。`raw.order_items` 的粒度不同：同一订单最多有 21 行商品记录。订单层和订单商品层不能直接与多笔支付记录同时连接，否则金额会发生乘法式重复计算；应先保持各自的事实粒度，或先聚合再连接。

订单状态共有八类，其中 `delivered` 为 96,478 笔。实际送达时间缺失 2,965 条，而预计送达时间没有缺失；必须区分“未送达所以没有送达时间”和“状态已送达但时间缺失”这两类情况。已送达订单中有 7,826 笔实际送达晚于预计日期，约占已送达订单的 8.1%。在 staging 层中，`is_delivery_late` 应只在两种送达时间均存在时给出 true 或 false；其他情况保留为 NULL，不能误标为未晚到。

进一步检查发现有 8 笔 `delivered` 订单缺少实际送达时间，这是需要显式标记的数据质量异常；同时有 6 笔 `canceled` 订单带有送达时间。staging 不应删除这些记录或擅自修正状态，而应保留原始值并增加异常标记，供交付时效指标过滤和后续数据治理说明使用。

预览转换后，这 8 笔订单都保留了下单时间和预计送达时间，但 `delivered_at` 为空，且 `has_delivery_timestamp_anomaly` 为 true。它们可以进入订单数量、客户和商品等分析，但不应参与实际配送时长或晚到率的分母。

已在数据库中创建 `staging.orders` 并验证：总行数和去重订单数均为 99,441，说明文本转换没有改变订单粒度；两类生命周期异常分别准确标记为 8 条和 6 条。下一步为 `order_id` 添加主键约束，让数据库在未来刷新时拒绝重复订单。

已确认 `staging_orders_pkey` 生效，定义为 `PRIMARY KEY (order_id)`。这将“一行一笔订单”的粒度约定落实为数据库约束：任何后续导入或脚本若产生重复订单，都会被立即拒绝。

`staging.order_items` 完成了日期和金额类型转换。112,650 行与 112,650 个 `(order_id, order_item_id)` 组合完全一致，证明商品粒度没有被改变；商品金额合计为 13,591,643.70，运费合计为 2,251,909.54。这两项金额是之后构建 `fact_order_items` 的不变量，任何建模操作都不能改变它们。

尝试对 `raw.payments.payment_value` 求和时得到 `function sum(text) does not exist`，因为 raw 层仍保留源 CSV 的文本类型。这个报错说明类型转换不能散落在每个分析查询中；应在 `staging.payments` 中统一把支付金额转为数值，之后所有事实表和指标都使用清洗后的字段。

`staging.payments` 验证为 103,886 行和 103,886 个 `(order_id, payment_sequential)` 组合，支付总额为 16,008,872.12。该金额与商品金额、运费金额分别属于不同业务口径，当前不假设它们必然相等；数据模型的职责是保留事实并说明口径，而不是人为调整金额使其看起来一致。

通过把 `staging.order_items` 与 `staging.payments` 直接按 `order_id` 连接，观察到连接后的行数等于“商品行数 × 支付行数”，且两种金额都被放大。这是多对多连接造成的乘法式重复，不是数据真实增长。正确做法是先在各自粒度内按订单聚合，再将两个订单级汇总连接到一行一订单的 `staging.orders`。

验证正确聚合后，即使一笔订单有 7 件商品和 3 次支付，查询仍只返回一行。示例中商品金额加运费为 421.70，而支付金额为 421.69，存在 0.01 的差异；这类微小差异应作为源数据的支付或舍入特征保留和记录，不能通过修改金额强行使两种口径相等。

客户表有 99,441 条订单客户记录和 96,096 位 `customer_unique_id` 不同的真实客户，说明至少有 3,345 条记录代表已有客户的后续订单。`customer_id` 的粒度与订单客户记录一致，而 `customer_unique_id` 才是复购、留存和 RFM 分析应使用的客户业务主键。

已创建并验证 `warehouse.dim_customer`：96,096 行代理键、96,096 个业务键均完全唯一。订单事实表将通过 `customer_id → customer_unique_id → customer_key` 的映射关联客户维度；这样保留了源订单的可追溯关系，同时让分析默认以真实客户为单位。

`warehouse.fact_orders` 已用“商品先聚合、支付先聚合、最后关联订单”的模式构建完成。它有 99,441 行和 99,441 个不同订单，商品金额总和仍为 13,591,643.70，支付金额总和仍为 16,008,872.12。结果证明订单事实表保持一行一订单，同时没有因为商品与支付的多对多关系重复计算金额。

自动化不变量测试出现“第一条绿、第二条红”：`fact_orders` 的一行一订单约束已验证通过；`fact_order_items` 尚未创建，因此金额不变性测试仍失败。这是符合预期的测试驱动状态，下一步创建订单商品事实表后应让第二条测试转绿。

`warehouse.fact_order_items` 创建后有 112,650 行和 112,650 个唯一订单商品组合，商品金额和运费金额分别保持为 13,591,643.70 与 2,251,909.54。重新运行两条仓库不变量测试后均通过：订单事实表保持一行一订单，订单商品事实表金额与 staging 层一致。这是 Day 6 的核心验收证据。

## Day 1-5：原始数据与已建表字段目录

### raw.customers

粒度：一行一个订单客户记录；主键：`customer_id`；所有字段类型：`text`。

`customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state`

### raw.orders

粒度：一行一笔订单；主键：`order_id`；所有字段类型：`text`。

`order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`

### raw.order_items

粒度：一行一件订单商品；组合主键：`(order_id, order_item_id)`；所有字段类型：`text`。

`order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`

### raw.payments

粒度：一行一次订单内支付；组合主键：`(order_id, payment_sequential)`；所有字段类型：`text`。

`order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`

### raw.reviews

粒度：一行一条订单评价关联；组合主键：`(review_id, order_id)`；所有字段类型：`text`。

`review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp`

### raw.products

粒度：一行一个商品；主键：`product_id`；所有字段类型：`text`。注意源字段拼写为 `lenght`，必须保留原样。

`product_id`, `product_category_name`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`

### raw.sellers

粒度：一行一个卖家；主键：`seller_id`；所有字段类型：`text`。

`seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state`

### raw.geolocation

粒度：一行一个地理位置观测；无源主键，因为同一邮编前缀可有多行；所有字段类型：`text`。

`geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state`

### raw.category_translation

粒度：一行一个商品类别翻译；主键：`product_category_name`；所有字段类型：`text`。

`product_category_name`, `product_category_name_english`

### audit.ingestion_runs

粒度：一行一次导入批次；主键：`run_id`。

`run_id` (`uuid`), `started_at` (`timestamptz`), `finished_at` (`timestamptz`), `status` (`text`), `source_file` (`text`), `source_hash` (`text`), `row_count` (`bigint`), `error_message` (`text`)

### staging.orders

粒度：一行一笔清洗后的订单；主键：`order_id`。

`order_id` (`text`), `customer_id` (`text`), `order_status` (`text`), `purchased_at` (`timestamp`), `approved_at` (`timestamp`), `delivered_to_carrier_at` (`timestamp`), `delivered_at` (`timestamp`), `estimated_delivery_at` (`timestamp`), `is_delivery_late` (`boolean`), `has_delivery_timestamp_anomaly` (`boolean`), `has_status_timestamp_anomaly` (`boolean`)

### staging.order_items

粒度：一行一件清洗后的订单商品；组合主键：`(order_id, order_item_id)`。

`order_id` (`text`), `order_item_id` (`integer`), `product_id` (`text`), `seller_id` (`text`), `shipping_limit_at` (`timestamp`), `price` (`numeric`), `freight_value` (`numeric`), `product_key` (`bigint`), `seller_key` (`bigint`)

### staging.payments

粒度：一行一次清洗后的订单支付；业务组合键：`(order_id, payment_sequential)`。

`order_id` (`text`), `payment_sequential` (`integer`), `payment_type` (`text`), `payment_installments` (`integer`), `payment_value` (`numeric`)

### staging.products

粒度：一行一个清洗后的商品；主键：`product_id`。

`product_id` (`text`), `category_name_pt` (`text`), `category_name_english` (`text`), `product_name_length` (`integer`), `product_description_length` (`integer`), `product_photos_qty` (`integer`), `product_weight_g` (`numeric`), `product_length_cm` (`numeric`), `product_height_cm` (`numeric`), `product_width_cm` (`numeric`), `has_missing_category` (`boolean`), `has_missing_translation` (`boolean`)

### staging.sellers

粒度：一行一个清洗后的卖家；主键：`seller_id`。

`seller_id` (`text`), `seller_zip_code_prefix` (`text`), `seller_city` (`text`), `seller_state` (`text`)

### staging.reviews

粒度：一行一条清洗后的订单评价关联；组合主键：`(review_id, order_id)`。

`review_id` (`text`), `order_id` (`text`), `review_score` (`integer`), `review_comment_title` (`text`), `review_comment_message` (`text`), `review_created_at` (`timestamp`), `review_answered_at` (`timestamp`)

### warehouse.dim_customer

粒度：一行一位真实客户；主键：`customer_key`；业务唯一键：`customer_unique_id`。

`customer_key` (`bigint`), `customer_unique_id` (`text`)

### warehouse.dim_product

粒度：一行一个商品；主键：`product_key`；业务唯一键：`product_id`。

`product_key` (`bigint`), `product_id` (`text`), `category_name_pt` (`text`), `category_name_english` (`text`), `product_name_length` (`integer`), `product_description_length` (`integer`), `product_photos_qty` (`integer`), `product_weight_g` (`numeric`), `product_length_cm` (`numeric`), `product_height_cm` (`numeric`), `product_width_cm` (`numeric`), `has_missing_category` (`boolean`), `has_missing_translation` (`boolean`)

### warehouse.dim_seller

粒度：一行一个卖家；主键：`seller_key`；业务唯一键：`seller_id`。

`seller_key` (`bigint`), `seller_id` (`text`), `seller_zip_code_prefix` (`text`), `seller_city` (`text`), `seller_state` (`text`)

### warehouse.dim_date

粒度：一行一个自然日；主键：`date_key`；业务唯一键：`date_value`。

`date_key` (`integer`, 格式 `YYYYMMDD`), `date_value` (`date`), `calendar_year` (`smallint`), `calendar_quarter` (`smallint`), `calendar_month` (`smallint`), `year_month` (`text`), `month_name` (`text`), `iso_week` (`smallint`), `iso_day_of_week` (`smallint`), `is_weekend` (`boolean`)

### warehouse.fact_orders

粒度：一行一笔订单；主键：`order_id`；外键：`customer_key → warehouse.dim_customer.customer_key`。

`order_id` (`text`), `customer_key` (`bigint`), `purchase_date_key` (`integer`), `source_customer_id` (`text`), `order_status` (`text`), `purchased_at` (`timestamp`), `approved_at` (`timestamp`), `delivered_to_carrier_at` (`timestamp`), `delivered_at` (`timestamp`), `estimated_delivery_at` (`timestamp`), `is_delivery_late` (`boolean`), `has_delivery_timestamp_anomaly` (`boolean`), `has_status_timestamp_anomaly` (`boolean`), `item_count` (`bigint`), `item_revenue` (`numeric`), `freight_revenue` (`numeric`), `payment_count` (`bigint`), `payment_value` (`numeric`)

### warehouse.fact_order_items

粒度：一行一件订单商品；组合主键：`(order_id, order_item_id)`；外键：`order_id → warehouse.fact_orders.order_id`。

`order_id` (`text`), `order_item_id` (`integer`), `product_id` (`text`), `seller_id` (`text`), `shipping_limit_at` (`timestamp`), `price` (`numeric`), `freight_value` (`numeric`), `product_key` (`bigint`), `seller_key` (`bigint`)

### warehouse.fact_payments

粒度：一行一次订单内支付；组合主键：`(order_id, payment_sequential)`；外键：`order_id → warehouse.fact_orders.order_id`。

`order_id` (`text`), `payment_sequential` (`integer`), `payment_type` (`text`), `payment_installments` (`integer`), `payment_value` (`numeric`)

### warehouse.fact_reviews

粒度：一行一条订单评价关联；组合主键：`(review_id, order_id)`；外键：`order_id → warehouse.fact_orders.order_id`。

`review_id` (`text`), `order_id` (`text`), `review_score` (`integer`), `review_comment_title` (`text`), `review_comment_message` (`text`), `review_created_at` (`timestamp`), `review_answered_at` (`timestamp`)

## Day 7：产品、卖家与日期维度

开始产品维度的数据质量检查时，连接 `raw.products` 与 `raw.category_translation` 后出现 `column reference "product_category_name" is ambiguous`。原因是两张表都含有同名字段；多表查询中所有同名列必须使用表别名限定，例如 `products.product_category_name`。这不是数据错误，而是 SQL 查询范围不明确；显式限定字段既避免报错，也让连接逻辑更容易审查。

产品表有 32,951 行和 32,951 个唯一商品。610 个商品缺少葡萄牙语类别，13 个商品已有类别但没有英文翻译。缺少类别与缺少翻译是不同的数据质量问题：前者没有可用分类，后者仍可用于葡萄牙语类别分析；在 staging 与维度表中分别保留空值和对应异常标记，不将两者混为一个 `Unknown` 值。

`staging.products` 已创建并复核为 32,951 行、32,951 个唯一商品，610 条缺类别和 13 条缺英文翻译标记均与 raw 层检查一致。源字段 `product_name_lenght` 在 staging 层被更正命名为 `product_name_length`，同时所有数值属性完成类型转换。

`warehouse.dim_product` 已验证为 32,951 行，代理键和 `product_id` 均完全唯一，并保留 610 条缺类别标记。产品事实表可以在后续通过 `product_key` 关联维度，同时保留类别缺失的可解释性。

卖家表有 3,095 行和 3,095 个唯一卖家，邮编前缀、城市和州均无缺失。邮编前缀是地理编码而非可计算数值，staging 层应保留为文本以保护前导零；城市统一为小写、州代码统一为大写，避免同一地点因格式不同被拆成多个类别。

`staging.sellers` 已验证为 3,095 行、3,095 个唯一卖家，覆盖 23 个州和 611 个城市；标准化过程没有改变卖家粒度。它将作为 `warehouse.dim_seller` 的唯一来源。

`warehouse.dim_seller` 已验证为 3,095 行，代理键和卖家业务键均唯一，并保留 23 个州。订单商品事实表下一步会以 `product_key` 和 `seller_key` 关联产品、卖家维度，减少对源业务 ID 的直接依赖。

在写入代理键前完成覆盖检查：112,650 条 `fact_order_items` 记录全部能映射到产品和卖家维度，缺失产品维度键和缺失卖家维度键均为 0。因此可以安全增加 `product_key`、`seller_key` 并设置为非空外键。

为事实表回填代理键时，首次 `UPDATE ... FROM` 将目标表别名写入了 `JOIN ... ON`，触发 PostgreSQL 的 FROM 作用域错误。目标表别名应在 `WHERE` 条件中与 FROM 表关联；错误发生在事务内时，先执行 `ROLLBACK` 才能撤销同一事务前面的 DDL 并恢复可执行状态。这说明事务不仅用于原子提交，也用于避免半完成的表结构修改。

修正 SQL 后，`fact_order_items` 的 112,650 条记录全部完成代理键回填：引用 32,951 个产品、3,095 个卖家，`product_key` 与 `seller_key` 缺失均为 0。两列现为非空外键，订单商品事实表已经以数仓代理键连接产品和卖家维度。

订单购买时间覆盖 2016-09-04 至 2018-10-17，期间只有 634 个实际有购买的日期。日期维度必须覆盖完整连续日历而不是仅保留活跃日期，否则零交易日期会在趋势、留存与分母计算中消失。该范围包含 774 个自然日，预计有 140 个无购买记录的日期也会在 `dim_date` 中保留。

`warehouse.dim_date` 已创建并验证为 774 个连续自然日，覆盖 2016-09-04 至 2018-10-17，其中 221 个周末日。它以 `YYYYMMDD` 格式的整数作为代理键，保留完整日历以支持零销售日期、周末效应和月度趋势分析。

订单事实表到日期维度的购买日期映射覆盖检查为 99,441 条订单、0 条缺失日期键。购买时间在原始数据中完整，因此可以将 `purchase_date_key` 设为非空外键；这使日、周、月、季度分析都可通过统一日期维度完成。

`purchase_date_key` 已回填并验证：99,441 笔订单映射到 634 个活跃购买日期，缺失日期键为 0。它是 `fact_orders` 到 `dim_date` 的非空外键，未来增长、Cohort 与 RFM 都应优先使用该日期维度而不是临时截断时间戳。

支付事实表创建前的关系检查显示 103,886 次清洗后支付均能关联到订单事实表，孤儿支付为 0。因此可为 `fact_payments` 设置 `(order_id, payment_sequential)` 组合主键和到 `fact_orders` 的外键，而不会因历史数据破坏约束。

`warehouse.fact_payments` 已验证为 103,886 行和 103,886 个唯一支付组合，支付总额保持 16,008,872.12，并包含 5 种支付方式。该表保留支付次数和支付方式的原始粒度；订单级支付总额仍应从 `fact_orders.payment_value` 读取，避免在订单商品表连接中重复计算。

评价表检查为 99,224 行和 99,224 个唯一 `(review_id, order_id)` 组合，孤儿评价为 0，评分范围为 1 到 5。评价文本保留在受控事实表中用于质量分析，但 Dashboard 和导出默认不展示原始评论内容，以避免无必要地暴露自由文本。

`staging.reviews` 已验证保持 99,224 个唯一评价订单组合，评分无缺失且范围为 1–5。评分、创建时间和答复时间已转为可分析类型；评论标题和内容保留为原始自由文本，不作为公开指标或下载字段。

`warehouse.fact_reviews` 已验证为 99,224 条唯一评价订单关联，平均评分为 4.086，其中 40,977 条含评论自由文本。评分可用于商品、卖家与履约质量的聚合分析；自由文本保留在受控事实表中，不作为默认 Dashboard 或导出内容。

## Day 8：将手工验证固化为可复现数仓

Navicat 出现 `Connection refused (10061)` 时，根因不是连接配置变化，而是 Docker Desktop 的 Linux 引擎未运行，`dockerDesktopLinuxEngine` 命名管道不存在；因此 PostgreSQL 容器没有监听本机 `127.0.0.1:5432`。启动 Docker Desktop 后，再执行项目目录中的 `docker compose up -d db`，数据库恢复健康并接受连接。排查顺序是：Docker 引擎 → `db` 容器状态 → `pg_isready` → Navicat，不能直接把端口拒绝连接归因于账号或密码。

Day 8 的工程目标是把 Day 6-7 在 Navicat 中验证的 staging、维度表、事实表和约束写入版本控制下的 SQL 文件，并提供一个构建脚本。这样任何人从空数据库开始都能按固定顺序重建同样的数仓，而不是依赖某次手工执行的历史。

已通过 Navicat 复核连接：数据库为 `olist`，连接用户为 `analytics`，服务器能返回当前 UTC 时间。此后 Day 8 的所有构建 SQL 都将以 `raw` 层为输入，确保本地手工已存在的 staging 与 warehouse 表可以被安全替换。

检查数仓外键元数据时，曾将 `constraint` 用作表别名并触发语法错误；它是 SQL 关键字，应改用 `con` 等非保留名称。系统目录查询同样需要遵守 SQL 语法与命名规则，错误发生在只读元数据检查中，不影响数据或表结构。

实际外键图已确认：`fact_orders` 分别依赖 `dim_customer` 和 `dim_date`；`fact_order_items` 依赖 `fact_orders`、`dim_product`、`dim_seller`；`fact_payments` 与 `fact_reviews` 均依赖 `fact_orders`。因此重建时必须先删除三张明细事实表，再删订单事实表，然后删四张维度表；创建则严格反向进行。`raw` 表和 `audit.ingestion_runs` 不在该删除范围内。

重建前的行数盘点最初尝试通过 CASE 和 LATERAL 统一处理多张表，但查询触发了聚合与外层列引用错误，也不利于阅读。对固定的十张核心表，使用显式 `UNION ALL` 更清楚、更易审查；生产构建则由 Python 按文件顺序执行 SQL，而不是把复杂动态 SQL 塞进 Navicat。

已通过命令行成功执行 `scripts/build_warehouse.py`，依次应用 `010_staging.sql`、`020_dimensions.sql` 和 `021_facts.sql`。该操作从 `raw` 重建了所有派生表，证明建模规则已进入版本控制代码；下一步以行数基线和自动化不变量测试确认重建结果没有偏离 Day 6-7 的手工验证。

重建后基线完全一致：`fact_orders` 为 99,441 行，`fact_order_items` 为 112,650 行，`fact_payments` 为 103,886 行，`fact_reviews` 为 99,224 行，且 raw 层行数未改变。仓库不变量测试 2/2 通过，分别证明订单事实表仍是一行一订单，订单商品事实表的商品金额仍与 staging 基线一致。Day 8 的验收结论是：数仓可由代码从原始数据重复构建，且结果与手工验证一致。

## Day 9：Cohort 与完整观察期复购

已将可复现数仓代码推送到 Gitee。只使用已送达订单时，数据观察窗口从 2016-09-15 到 2018-08-29；最后日期 `2018-08-29` 是计算 30、60、90 天复购资格的全局截止点。客户首购日在截止点前至少 30、60 或 90 天，才可分别进入对应复购率的分母；否则属于右删失样本，不能因为尚未观察满窗口而误标为“未复购”。

共有 93,358 位客户至少有一笔已送达订单；其中 86,909 位具备完整 30 天窗口、81,265 位具备完整 60 天窗口、75,387 位具备完整 90 天窗口。资格人数按窗口变长而递减，这反映观察期边界而非客户流失；复购率的每个分母必须使用对应窗口的资格人数。

按“首购后的自然日”初步统计，完整观察期内复购客户为 30 天 577、60 天 831、90 天 978，随窗口扩大而递增。该初步口径将下单时间截断到日期，可能遗漏首购同日稍晚发生的另一笔订单；最终集市与模型标签必须改用精确 `purchased_at` 时间戳，以避免错误排除同日复购。

按精确时间戳重新计算后的最终结果为：30 天资格客户 86,909、复购客户 1,136、复购率 1.307%；60 天资格客户 81,265、复购客户 1,372、复购率 1.688%；90 天资格客户 75,387、复购客户 1,514、复购率 2.008%。相比按日期的初步结果，复购人数明显增加，证实同一自然日的后续订单会影响结论；本项目后续 Cohort、指标集市与机器学习标签统一使用时间戳边界。

按客户首次已送达购买月构建 Cohort：2016-09 有 1 位、2016-10 有 262 位、2016-11 没有首购客户；2017-11 Cohort 最大，为 7,060 位，2018-08 为 6,144 位。2016-09 是数据开始月、2018-08 是数据结束月，均不是完整自然月；留存矩阵必须将观察月份完整性单独标记，不能把边界月的低活动直接解释为留存流失。

初版 Cohort 明细验证了所有 `months_since_cohort = 0` 的留存均为 100%，并正确标记 2016-09 与 2018-08 的观察月不完整。但查询只返回有活动的客户月，例如 2016-10 Cohort 跳过了许多中间月份；这些缺行在业务上代表 0 位回购，不是未知数据。正式留存矩阵需要先生成 Cohort 月与活动月的完整网格，再用 `COALESCE(..., 0)` 填零，否则图表会把零留存月份错误隐藏。

对 2016-10 Cohort 的补零验证产生 23 个连续观察月：首月 262/262 为 100%，第 1–5 月均明确为 0，后续仅少数月份有 1–2 位回购客户；第 22 月对应 2018-08，被正确标记为不完整。该实验验证了完整网格与 `COALESCE` 的必要性，正式 `marts.cohort_retention` 将保留 Cohort 月、活动月、相对月、Cohort 规模、留存人数、留存率和观察月完整性。

`marts.cohort_retention` 已创建并验证为 278 个 Cohort×活动月单元、23 个 Cohort、23 个第 0 月 100% 留存。共有 24 个不完整观察单元：2016-09 的数据开始月 1 个，加上每个 Cohort 的 2018-08 数据结束月 23 个。该标记使 Dashboard 和业务结论能够排除截断月份，而不把数据边界误解为留存下降。

抽样查看第 1–3 月留存时发现，只有 1 位或 262 位客户的早期 Cohort 出现 0% 或 100% 的大幅波动，不能与数千人的 Cohort 做等权比较。2018 年 Cohort 的第 1 月留存约为 0.350%–0.593%，后续月通常进一步下降。汇总留存曲线应按 Cohort 客户数加权，即 `SUM(retained_customers) / SUM(cohort_customers)`，使每位客户而非每个 Cohort 拥有相同权重。

按客户数加权的完整观察月留存为：第 1 月 0.480%（390/81,265）、第 2 月 0.341%（257/75,387）、第 3 月 0.261%（180/68,881）、第 4 月 0.268%（167/62,299）、第 5 月 0.238%（132/55,525）、第 6 月 0.236%（116/49,237）。第 4 月略高于第 3 月不构成矛盾，因为指标是“该月是否再次购买”的期间活跃率，而不是要求逐月连续活跃的生存率；可用于每个相对月的完整 Cohort 数从 21 下降至 16，体现观察期资格过滤。

## Day 10：Customer 360 与 RFM 分群

RFM 仅使用 `delivered` 订单：Recency 为全局观察截止点到最近一次已送达购买的天数，Frequency 为已送达订单数，Monetary 为订单级 `item_revenue` 的累计商品金额。Monetary 不混入运费，也不从支付明细与订单商品明细的直接连接中计算，以避免再次引入金额重复；开始分群前需先检查 Frequency 是否大量集中为 1，决定不能盲目使用普通分位数分箱。

Frequency 分布高度偏斜：90,557 位客户（97.000%）仅有 1 笔已送达订单，2,573 位有 2 笔，181 位有 3 笔，最高为 15 笔。仅 2,801 位客户有至少两笔订单，因此普通 `qcut` 或四分位分箱会因重复的 `F=1` 边界而失去区分能力。后续分群将保留原始 Frequency，并明确标记单次购买客户，而不是用貌似精确但不稳定的频次分位数。

Recency 分位数为 0、113、218、345、713 天；客户累计商品金额的 25/50/75 分位数为 47.65、89.73、154.7375，最高为 13,440.00。R 与 M 可使用四分位分数：更近购买或更高金额得分更高；Frequency 不做分位数，而保留原始订单数并按 `1`、`2`、`3+` 形成稳定业务规则。消费额最高值远高于上四分位，表明客户价值高度集中，分群结论需同时报告人数和金额贡献。

策略分群结果为：`needs_attention` 23,003 位（24.640%）贡献 5,441,216.62 商品金额（41.154%）；`potential` 22,360 位（23.951%）贡献 5,179,383.45（39.174%）；`one_time_low_value` 46,221 位（49.509%）贡献 2,177,855.24（16.472%）；`high_value` 仅 1,316 位（1.410%）贡献 394,634.49（2.985%）；其余 `standard` 为 458 位。高价值但沉默、以及近期高金额未复购的两类客户合计占 48.591% 客户却贡献 80.328% 商品金额，是后续运营策略最应优先验证的对象。

已将该探索规则固化为 `marts.customer_360`，粒度为一行一位至少有一笔已送达订单的客户，主键为 `customer_key`，并外键关联 `warehouse.dim_customer`。字段为：`customer_key` (`bigint`), `snapshot_at` (`timestamp`), `first_purchase_at` (`timestamp`), `last_purchase_at` (`timestamp`), `recency_days` (`integer`), `frequency_orders` (`bigint`), `monetary_item_revenue` (`numeric`), `freight_revenue` (`numeric`), `payment_value` (`numeric`), `distinct_category_count` (`bigint`), `avg_review_score` (`numeric`), `avg_delivery_days` (`numeric`), `r_score` (`integer`), `f_score` (`integer`), `m_score` (`integer`), `customer_segment` (`text`), `eligible_for_90d` (`boolean`), `repurchased_within_90d` (`boolean`)。其中 `snapshot_at` 是全局数据观察截止时间；`repurchased_within_90d` 只在 `eligible_for_90d = true` 时才有真/假值，否则为 `NULL`，从而避免将观察期不足的客户误标为未复购。

永久表重建后的分群为：`high_value` 1,310 位、商品金额 393,299.50；`potential` 22,290 位、5,162,935.18；`needs_attention` 23,079 位、5,458,999.88；`one_time_low_value` 46,221 位、2,177,855.24；`standard` 458 位、28,408.31。与临时探索统计存在少量差异时，应以版本控制的正式 SQL 和可重复构建结果为准，而非复制过的临时查询。

首次实现将 90 天标签写成每个客户一条相关子查询，构建长时间运行并出现临时文件 I/O。排查 PostgreSQL 活动会话后确认，停止外层测试不会自动停止其子进程；应先取消遗留数据库查询。性能修复不是简单加超时，而是将复购判断改为 `repurchase_labels` 预聚合 CTE：先在客户粒度计算 90 天内是否存在后续订单，再连接到 Customer 360。重建测试恢复为约 2 秒，说明在分析 SQL 中必须优先控制扫描次数和连接粒度。
