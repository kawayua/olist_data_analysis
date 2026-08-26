# 模拟营销实验与 Uplift 演示实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展时间安全首单特征，并以可复现模拟 A/B 实验、业务成本阈值和模拟 uplift 演示替换现有的纯 ROI 假设页。

**Architecture:** `marts.ml_customer_features` 提供仅在首单送达时可见的数值与类别特征；训练管线在严格时间切分下处理两种特征并保存扩展 schema。`src/ml/experiment.py` 作为不依赖 Streamlit 的实验核心，生成冻结的客户分组、模拟触达/90 天结果、阈值分析与模拟 uplift 排序。第 6 页只收集显式假设并展示模拟标识、平衡检查、成本决策和未来真实 CSV 契约。

**Tech Stack:** PostgreSQL、Python 3.13、pandas、numpy、scikit-learn、LightGBM、Streamlit、Plotly、pytest、Ruff。

**Spec:** `docs/superpowers/specs/2026-08-26-simulated-experiment-uplift-design.md`

## Global Constraints

- `prediction_time` 固定为首笔已送达订单的 `delivered_at`；不得使用评论、未来订单、未来金额或标签作为特征。
- 所有模拟输出必须携带 `data_origin="simulation"`，页面必须说明其不是实际投放因果结论。
- 只在训练期拟合类别编码、填补与缩放；模型选择、校准和最终测试仍严格时间隔离。
- 固定同一输入与随机种子必须得到相同实验分组和结果。
- 同时比较 Top 1%、3%、5%、10%；推荐按风险规则下的预期增量利润，不按 Lift 或 ROI 单独选择。
- 本轮不接入 CRM、渠道或真实实验结果；仅输出未来真实导入的 CSV 契约。
- 不修改或提交现有无关变更、`.pytest-*`、`docker` 或模型生成物，除非重训步骤明确要求更新模型产物。

---

## File Structure

- Modify: `sql/warehouse/020_dimensions.sql` — 使客户州成为受治理的客户维度字段。
- Modify: `sql/marts/035_ml_customer_features.sql` — 产生扩展的、时间安全的首单特征。
- Modify: `src/analytics/repository.py` — 明确读取扩展后的在线评分特征，且不读取标签。
- Modify: `src/ml/train.py` — 定义数值/类别特征，并为三种候选构建共同预处理器。
- Modify: `src/ml/artifacts.py`、`scripts/train_model.py` — 保存扩展 schema、含多个触达分位的指标和正确的重要性。
- Create: `src/ml/experiment.py` — 实验配置、可复现模拟、平衡/效果/阈值分析和模拟 uplift 排序。
- Modify: `src/ml/roi.py` — 复用成本和盈亏平衡辅助计算，移除把相对 uplift 假设伪装成推荐依据的职责。
- Modify: `app/pages/6_营销ROI模拟器.py` — 新的“营销实验与增量评估”页面。
- Create: `docs/data-contracts/marketing-experiment-csv.md` — 未来真实 `assignments.csv`、`touchpoints.csv`、`outcomes_90d.csv` 的字段与校验契约。
- Modify: `docs/learning/machine-learning-summary.md` — 记录排序模型、实验和 uplift 的职责边界。
- Modify/Create tests: `tests/sql/test_customer_value_repurchases.py`、`tests/analytics/test_repository.py`、`tests/ml/test_evaluate.py`、`tests/ml/test_train.py`、`tests/ml/test_artifacts.py`、`tests/ml/test_experiment.py`、`tests/ml/test_roi.py`、`tests/visualization/test_dashboard_pages.py`。

### Task 1: 扩展受治理且时间安全的首单特征

**Files:** Modify `sql/warehouse/020_dimensions.sql`, `sql/marts/035_ml_customer_features.sql`, `src/analytics/repository.py`; Test `tests/sql/test_customer_value_repurchases.py`, `tests/analytics/test_repository.py`.

**Interfaces:**
- `marts.ml_customer_features` produces the existing six fields plus `customer_state`, `first_order_primary_category`, `first_order_max_item_revenue`, `first_order_average_item_revenue`, `first_order_freight_rate`, `first_order_payment_type_count`, `first_order_max_installments`, `first_order_seller_state_count`, `first_order_cross_state`, `first_order_estimated_delivery_days`, `first_order_delivery_vs_estimate_days`, `first_order_is_late`, `first_order_purchase_month`, `first_order_purchase_weekday`, `first_order_approval_hours`, and `first_order_carrier_handoff_hours`.
- `AnalyticsRepository.ml_customer_features_for_scoring()` selects `customer_key` plus exactly `FEATURE_COLUMNS`, never `repurchased_within_90d` or an unknown `SELECT *`.

- [ ] **Step 1: 写失败测试**

在 SQL 集成测试中断言集市包含上述字段、`feature_available_at = prediction_time`、每个字段可由首单或送达前/送达时事实导出，并且 `fact_reviews` 字段和未来字段不在列中。在 repository mock 测试中断言扩展特征被显式 SELECT，标签和 `future_` 文本仍不存在。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/sql/test_customer_value_repurchases.py::test_ml_customer_features_exposes_extended_time_safe_columns tests/analytics/test_repository.py::test_repository_reads_only_time_safe_features_for_model_scoring -v --basetemp .pytest-ml-features-red`。

预期：新列断言和显式查询断言失败，而现有集市仍可构建。

- [ ] **Step 3: 最小实现**

在 `dim_customer` 中受治理地写入客户州；在 `035_ml_customer_features.sql` 中以首单订单、`fact_order_items`、`dim_product`、`fact_payments` 与 `dim_seller` 聚合出上述字段。商品主品类必须采用确定性规则（金额降序、类别名升序打破并列）；各比例使用 `NULLIF` 避免除零；延迟和相对预计时长只使用 `delivered_at` 时已经存在的时间戳。扩展 repository 的显式列清单。

- [ ] **Step 4: 验证 GREEN**

运行：`py -3.13 -m pytest tests/sql/test_customer_value_repurchases.py tests/analytics/test_repository.py -v --basetemp .pytest-ml-features-green`，随后 `py -3.13 scripts/build_marts.py`。确认集市重建成功且测试通过。

- [ ] **Step 5: 提交**

`git add sql/warehouse/020_dimensions.sql sql/marts/035_ml_customer_features.sql src/analytics/repository.py tests/sql/test_customer_value_repurchases.py tests/analytics/test_repository.py && git commit -m "feat: expand time-safe repurchase features"`

### Task 2: 训练管线支持数值与类别特征，并报告多阈值排序表现

**Files:** Modify `src/ml/train.py`, `src/ml/evaluate.py`, `src/ml/artifacts.py`, `scripts/train_model.py`; Test `tests/ml/test_train.py`, `tests/ml/test_evaluate.py`, `tests/ml/test_artifacts.py`.

**Interfaces:**
- `NUMERIC_FEATURE_COLUMNS` and `CATEGORICAL_FEATURE_COLUMNS` compose `FEATURE_COLUMNS`; `FEATURE_MEANINGS` has one Chinese label per field.
- `evaluate_at_fractions(y_true, scores, fractions=(0.01, 0.03, 0.05, 0.10)) -> dict[str, ModelMetrics]` returns one metric record per fraction.
- persisted `metrics.json` carries `threshold_metrics` for selection baseline and final test; `feature_schema.json` persists both feature type groups and forbidden fields.

- [ ] **Step 1: 写失败测试**

构造一个同时包含数值列、类别列和缺失类别的小训练帧，断言 Logistic、随机森林和 LightGBM 都能生成 `[0, 1]` 的概率；断言未知类别在评分时不报错。构造 100 条标签/分数，断言 `evaluate_at_fractions` 恰有 `1%`、`3%`、`5%`、`10%` 四项。断言 artifact schema 保留特征类型与每个扩展字段的中文含义。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/ml/test_train.py tests/ml/test_evaluate.py tests/ml/test_artifacts.py -v --basetemp .pytest-ml-training-red`。

预期：缺少新常量、类别预处理或多阈值评估接口而失败。

- [ ] **Step 3: 最小实现**

用 `ColumnTransformer` 对数值列执行中位数填补（Logistic 再标准化），对类别列执行最频繁值填补与 `OneHotEncoder(handle_unknown="ignore")`；候选模型共用相同特征边界。评估器仅对排名分数计算各分位指标；在训练脚本的选择集和最终测试集写入四个阈值结果。特征重要性从变换后的特征名聚合回原始字段，避免 one-hot 列把解释表膨胀为技术列。

- [ ] **Step 4: 验证 GREEN 并重训**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_train.py tests/ml/test_evaluate.py tests/ml/test_artifacts.py -v --basetemp .pytest-ml-training-green
py -3.13 -m ruff check src/ml scripts/train_model.py tests/ml
py -3.13 scripts/train_model.py
```

人工检查 `artifacts/models/feature_schema.json` 无禁止字段，`metrics.json` 含四种阈值，模型卡仍写明关联不等于因果。

- [ ] **Step 5: 提交**

`git add src/ml/train.py src/ml/evaluate.py src/ml/artifacts.py scripts/train_model.py tests/ml/test_train.py tests/ml/test_evaluate.py tests/ml/test_artifacts.py artifacts/models && git commit -m "feat: evaluate enriched repurchase ranking features"`

### Task 3: 建立可复现模拟实验、成本阈值与模拟 uplift 服务

**Files:** Create `src/ml/experiment.py`; Modify `src/ml/roi.py`; Test `tests/ml/test_experiment.py`, `tests/ml/test_roi.py`.

**Interfaces:**
- `ExperimentConfig(name, seed, treatment_fraction, channel, unit_cost, coupon_cost, average_repurchase_margin, uplift_by_score_decile)` validates explicit simulation assumptions.
- `simulate_experiment(scored_customers: pd.DataFrame, config: ExperimentConfig) -> ExperimentRun` produces `assignments`, `touchpoints`, and `outcomes_90d` frames with `data_origin="simulation"`.
- `summarize_experiment(run) -> ExperimentSummary` exposes arm sizes, score-balance difference, repurchase-rate difference, 95% Wilson/Newcombe interval, incremental margin, cost, net incremental profit and ROI.
- `evaluate_contact_thresholds(run, fractions=(0.01, 0.03, 0.05, 0.10), risk_floor=0.0) -> pd.DataFrame` and `recommend_threshold(table) -> pd.Series | None` apply the profit/risk/tie-break rule.
- `fit_simulated_uplift(assignments, outcomes, feature_frame) -> UpliftModel` and `rank_by_expected_incremental_profit(...) -> pd.DataFrame` are explicitly restricted to `data_origin="simulation"`.

- [ ] **Step 1: 写失败测试**

使用 100 个确定性客户分数和两个不同分位的绝对提升假设：断言同 seed 两次运行的三张表逐行相同、不同 seed 的分组不同、每客户每实验恰有一个分组、对照组无触达成本、处理组成本正确且所有记录均为 `simulation`。断言已知处理/对照输入的复购率差、成本、利润和区间方向正确。断言阈值表包含 1/3/5/10%，推荐只在区间下界达到风险线时按净增量利润选择并在平局时选更小分位。断言模拟 uplift 排序拒绝 `real` 来源或不完整观察窗口。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/ml/test_experiment.py tests/ml/test_roi.py -v --basetemp .pytest-experiment-red`。

预期：`src.ml.experiment` 和阈值接口不存在而失败。

- [ ] **Step 3: 最小实现**

仅在纯 Python 模块中实现随机分层分组：按校准分数的稳定 `qcut` 分位分层，以 `numpy.random.default_rng(seed)` 在层内分配处理组。对照复购结果采样自裁剪后的校准概率；处理组用该概率加对应分位的公开绝对 uplift 后采样。每条结果使用分组后 90 天窗口、完整观察标志与毛利；触达成本仅对处理组累计。用二项比例差的 Newcombe/Wilson 95% 区间报告增量复购率。将原 ROI 模块缩为共享的非负成本、金额和盈亏平衡辅助函数，禁止其继续生成“因果提升推荐”。

在模拟完整样本上用 T-learner（处理组/对照组各一个与 Task 2 相同安全预处理的 Logistic 模型）预测条件结果差；名单按 `预测 uplift × 平均复购毛利 − 单次成本` 降序，而不是自然复购概率或 Lift 降序。

- [ ] **Step 4: 验证 GREEN**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_experiment.py tests/ml/test_roi.py -v --basetemp .pytest-experiment-green
py -3.13 -m ruff check src/ml tests/ml
```

确认每项产生的 DataFrame 不含真实客户 PII、`data_origin` 不可缺失、固定种子结果可重复。

- [ ] **Step 5: 提交**

`git add src/ml/experiment.py src/ml/roi.py tests/ml/test_experiment.py tests/ml/test_roi.py && git commit -m "feat: add reproducible simulated marketing experiments"`

### Task 4: 重构实验页面并发布未来真实导入契约

**Files:** Modify `app/pages/6_营销ROI模拟器.py`, `app/components/navigation.py`; Create `docs/data-contracts/marketing-experiment-csv.md`; Modify `docs/learning/machine-learning-summary.md`, `tests/visualization/test_dashboard_pages.py`.

**Interfaces:**
- 页面标题为“营销实验与增量评估”，仍使用 `pages/6_营销ROI模拟器.py` 路径。
- UI consumes only `load_scored_customers()`, `ExperimentConfig`, `simulate_experiment`, `summarize_experiment`, `evaluate_contact_thresholds`, and simulated uplift ranking.
- 文档定义 future-only CSV headers: `assignments.csv`, `touchpoints.csv`, `outcomes_90d.csv` and their validation rules; it offers no upload widget in this scope.

- [ ] **Step 1: 写失败测试**

在页面静态测试断言：第 6 页含“营销实验与增量评估”“模拟实验”“Top 1%”“Top 3%”“Top 5%”“Top 10%”与“真实数据接入契约”；不再含旧的“提升率是业务假设”主流程或 `use_container_width`。断言数据契约文档包含三种 CSV 名称、`data_origin`、90 天窗口、重复分组和非负成本校验。

- [ ] **Step 2: 验证 RED**

运行：`py -3.13 -m pytest tests/visualization/test_dashboard_pages.py -v --basetemp .pytest-experiment-page-red`。

预期：新标题、阈值与模拟提示不存在而失败。

- [ ] **Step 3: 最小实现**

使用原有中文驾驶舱主题与 `render_kpis`。先渲染实验参数和永久模拟提示，再执行缓存的客户评分与纯计算模拟；按信息层次展示：实验设计、名单阈值表及推荐、随机化平衡、处理/对照效果和区间、模拟 uplift 名单价值、未来真实 CSV 契约。无法达到风险线时，用警示呈现“暂不扩大投放”与可承受成本，不把负数隐藏。Plotly 图只使用中文轴名、直接标签和零线；所有 `st.dataframe` 使用 `width="stretch"` 或默认伸展宽度，绝不使用 `use_container_width`。

在数据契约文档给出字段、类型、样例行和导入拒绝条件；在学习文档说明“排序模型—模拟实验—真实 uplift”的三层证据强度。

- [ ] **Step 4: 验证 GREEN 与运行检查**

运行：

```powershell
py -3.13 -m pytest tests/visualization/test_dashboard_pages.py tests/ml tests/analytics -v --basetemp .pytest-experiment-page-green
py -3.13 -m ruff check app src/ml scripts tests/ml tests/analytics tests/visualization
```

检查 850* 端口的已有 Streamlit 进程；仅在用户同意启动或刷新正确工作目录的实例后，使用 `py -3.13 -m streamlit run app/Home.py --server.port <free-port>`，人工确认模拟标签、Top 阈值表、负收益风险信息和真实导入契约可见。

- [ ] **Step 5: 提交**

`git add app/pages/6_营销ROI模拟器.py app/components/navigation.py docs/data-contracts/marketing-experiment-csv.md docs/learning/machine-learning-summary.md tests/visualization/test_dashboard_pages.py && git commit -m "feat: present simulated marketing experiment workflow"`

### Task 5: 端到端验收与项目状态更新

**Files:** Modify `tests/integration/test_verify_project.py`, relevant current project report only if it labels the ROI/ML scope as unfinished; Test `tests/integration/test_verify_project.py`.

**Interfaces:**
- Verification confirms model schema feature safety, simulated experiment reproducibility, decision threshold behavior, page copy, and documentation contract together.

- [ ] **Step 1: 写失败测试**

在 `test_verify_project.py` 加一项可静态验证的交付清单：设计文档、数据契约、实验服务、特征 schema 的禁止字段列表、阈值函数和模拟标签均存在。

- [ ] **Step 2: 验证 RED、实现和 GREEN**

先运行新增用例，确认缺少清单项时失败；补齐实际产物而非放宽断言。运行：

```powershell
py -3.13 -m pytest -q --basetemp .pytest-experiment-final
py -3.13 -m ruff check app src scripts tests
py -3.13 scripts/verify_project.py
```

仅在命令均为零退出且数据库可用时，使用 Navicat 执行只读验收查询：确认扩展集市列、90 天标签完整性与不存在评论特征；记录实际行数和列名结果。

- [ ] **Step 3: 提交**

`git add tests/integration/test_verify_project.py docs/reports && git commit -m "test: verify simulated experiment delivery"`

## Self-Review

- Spec coverage: Task 1 实现时间安全特征，Task 2 实现训练、校准产物与四阈值排序，Task 3 实现可复现实验/效果/成本/uplift，Task 4 实现页面与真实导入契约，Task 5 执行端到端验收。
- Placeholder scan: 每个任务明确了文件、接口、失败测试、运行命令、最小实现和验收边界；不存在 TBD、TODO 或“类似前一任务”。
- Type consistency: 页面只消费 `ExperimentConfig` 和 Task 3 导出的分析结果；未来 CSV 文件只在 Task 4 文档中定义，未被误实现为本轮上传功能；所有模型特征由 Task 1 的集市列和 Task 2 的 `FEATURE_COLUMNS` 同步定义。
