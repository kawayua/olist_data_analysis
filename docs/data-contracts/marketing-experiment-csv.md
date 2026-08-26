# 营销实验真实数据接入契约

当前平台只生成 `data_origin=simulation` 的教学记录；未来真实接入使用同一口径但必须标记为 `real`。

- `assignments.csv`：`experiment_code,customer_key,arm_name,assigned_at,model_version,repurchase_score,score_decile`；同实验客户只能分组一次。
- `touchpoints.csv`：`experiment_code,customer_key,channel,sent_at,delivery_status,unit_cost,coupon_cost`；触达不得早于分组，成本必须非负。
- `outcomes_90d.csv`：`experiment_code,customer_key,observation_start,observation_end,is_observation_complete,repurchased_within_90d,repeat_order_count,repeat_item_revenue,incremental_margin`；必须完整覆盖 90 天。

拒绝未知客户、重复分组、未知渠道、负成本和不完整观察窗口。真实数据满足处理/对照完整与平衡检查后，才允许训练真实 uplift 模型。
