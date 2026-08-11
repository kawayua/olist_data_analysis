# Olist 原始数据

本项目使用 Olist Brazilian E-Commerce Public Dataset。原始数据由 Olist 发布，包含客户、订单、订单商品、支付、评价、商品、卖家、地理位置和品类翻译九张 CSV 表。

## 获取方式

1. 从 [Olist 原始数据页](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 下载数据。
2. 解压后将以下九个文件直接放入 `data/raw/`：

   - `olist_customers_dataset.csv`
   - `olist_orders_dataset.csv`
   - `olist_order_items_dataset.csv`
   - `olist_order_payments_dataset.csv`
   - `olist_order_reviews_dataset.csv`
   - `olist_products_dataset.csv`
   - `olist_sellers_dataset.csv`
   - `olist_geolocation_dataset.csv`
   - `product_category_name_translation.csv`

3. 后续运行导入脚本前，数据契约会检查这九个文件及其列结构。

GitHub 上的 [数据说明镜像](https://github.com/spdrio/Brazilian-E-Commerce-Public-Dataset-by-Olist) 可用于查看业务背景和表关系。原始 CSV 不提交到 Git：文件较大，而且项目应保留原始来源与许可信息，而不是重新分发副本。

## 使用边界

这是经过匿名化处理的历史数据。它只能用于作品集分析和学习，不代表 Olist 当前经营情况。重新分发任何数据前，应再次核对原始数据页的许可条款。
