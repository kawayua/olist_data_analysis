# Day 16 Boosted Repurchase Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不引入未来信息的前提下，训练、选择、校准并审计一个比首单金额规则更有效的 90 天复购排序模型。

**Architecture:** 从 `marts.ml_customer_features` 读取 Day 14 的首单时点特征，并按 `prediction_time` 划分训练、模型选择、校准和最终测试四段。LightGBM、Random Forest 与 Logistic Regression 均只拟合训练段；LightGBM 的早停集从训练段末尾进一步切出，绝不使用模型选择段。以模型选择段的 PR-AUC（主）和 Lift@10%（并列时的业务裁决）选择候选模型，随后只用校准段拟合 sigmoid 概率映射，最终测试段只在流程结束时评估一次。

**Tech Stack:** Python 3.13, pandas, scikit-learn 1.8, LightGBM 4.6, joblib, pytest, Ruff, PostgreSQL/SQLAlchemy。

## Global Constraints

- 特征只能使用 `src/ml/train.py` 中定义的 Day 14 `FEATURE_COLUMNS`；禁止加入评论、后续订单、最终 RFM 或任何预测时点后的字段。
- 样本必须满足 `eligible_for_90d` 且标签非空；`prediction_time` 是唯一的时间划分依据。
- 四个外部时间段顺序固定为训练、选择、校准、最终测试；最终测试集不得参与拟合、早停、调参或选择。
- 候选选择以 PR-AUC 为主，PR-AUC 相同才比较 Lift@10%，不得使用 Accuracy。
- 仅对概率调用 `evaluate_probabilities` 和 Brier score；首单金额规则继续使用 `evaluate_ranking`，其 Brier score 必须为 `null`。
- 公开产物与文档使用中文字段解释；Python、SQL 和 DataFrame 内部列名保持英文。
- 在 Windows 下使用 `py -3.13` 运行 pytest、Ruff 和脚本。
- 不修改或暂存既有的 `docs/learning/week-2.md`、旧计划文件、`.pytest-basetemp/` 和其他无关改动。

---

## File Structure

- Modify: `src/ml/dataset.py` — 增加严格顺序的四段时间切分。
- Modify: `tests/ml/test_dataset.py` — 验证四段无重叠、严格递增。
- Modify: `src/ml/train.py` — 构建三类候选模型、训练 LightGBM 早停模型、选择最佳候选，并提供可复用的概率预测接口。
- Modify: `tests/ml/test_evaluate.py` — 验证候选集合、选择规则和防泄漏特征边界。
- Create: `src/ml/calibration.py` — 用独立校准期拟合并应用 sigmoid 概率映射。
- Create: `tests/ml/test_calibration.py` — 验证校准器输出合法概率且不接受单一类别标签。
- Create: `src/ml/artifacts.py` — 将选中模型、特征 schema、指标、代表客户预测和模型卡写入可审计产物。
- Create: `tests/ml/test_artifacts.py` — 验证训练产物完整、可读取且不丢失校准信息。
- Modify: `scripts/train_model.py` — 编排时间切分、候选比较、校准、一次最终测试和产物落盘。
- Modify: `docs/learning/week-2.md` — 记录 Day 16 的模型选择、校准与结果解读。

### Task 1: 建立四段时间切分与训练期内部早停边界

**Files:**
- Modify: `src/ml/dataset.py`
- Modify: `tests/ml/test_dataset.py`

**Interfaces:**
- Consumes: 输入 DataFrame 必须有 `prediction_time` 列。
- Produces: `temporal_four_way_split(frame, train_end, selection_end, calibration_end) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]`，依次返回 `train`、`selection`、`calibration`、`test`。
- Produces: `split_training_for_early_stopping(train_frame, early_stopping_fraction=0.1) -> tuple[pd.DataFrame, pd.DataFrame]`，按时间返回训练主体和训练期末尾的早停集。

- [ ] **Step 1: 写出四段切分的失败测试**

在 `tests/ml/test_dataset.py` 增加：

```python
def test_temporal_four_way_split_keeps_all_periods_strictly_ordered():
    frame = pd.DataFrame(
        {"prediction_time": pd.date_range("2018-01-01", periods=8, freq="MS")}
    )

    train, selection, calibration, test = temporal_four_way_split(
        frame,
        pd.Timestamp("2018-02-15"),
        pd.Timestamp("2018-04-15"),
        pd.Timestamp("2018-06-15"),
    )

    assert train.prediction_time.max() < selection.prediction_time.min()
    assert selection.prediction_time.max() < calibration.prediction_time.min()
    assert calibration.prediction_time.max() < test.prediction_time.min()
```

再增加：

```python
def test_early_stopping_split_uses_only_the_end_of_training_period():
    train_frame = pd.DataFrame(
        {"prediction_time": pd.date_range("2018-01-01", periods=10, freq="D")}
    )

    fitting, early_stopping = split_training_for_early_stopping(train_frame, 0.2)

    assert len(fitting) == 8
    assert len(early_stopping) == 2
    assert fitting.prediction_time.max() < early_stopping.prediction_time.min()
```

- [ ] **Step 2: 运行测试，确认失败**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_dataset.py -v --basetemp "$env:TEMP\day16-split-red"
```

预期：因两个函数尚未定义而收集失败或 ImportError。

- [ ] **Step 3: 实现最小的严格时间切分**

在 `src/ml/dataset.py` 增加：

```python
def temporal_four_way_split(
    frame: pd.DataFrame,
    train_end: pd.Timestamp,
    selection_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = frame.copy()
    ordered["prediction_time"] = pd.to_datetime(ordered["prediction_time"])
    ordered = ordered.sort_values("prediction_time")
    train = ordered.loc[ordered["prediction_time"] <= pd.Timestamp(train_end)]
    selection = ordered.loc[
        (ordered["prediction_time"] > pd.Timestamp(train_end))
        & (ordered["prediction_time"] <= pd.Timestamp(selection_end))
    ]
    calibration = ordered.loc[
        (ordered["prediction_time"] > pd.Timestamp(selection_end))
        & (ordered["prediction_time"] <= pd.Timestamp(calibration_end))
    ]
    test = ordered.loc[ordered["prediction_time"] > pd.Timestamp(calibration_end)]
    return train.copy(), selection.copy(), calibration.copy(), test.copy()
```

并实现 `split_training_for_early_stopping`：先按 `prediction_time` 升序排序，拒绝 `early_stopping_fraction` 不在 `(0, 1)` 的输入；用 `ceil(len(ordered) * early_stopping_fraction)` 取得至少一行的训练期末尾行。若切分后训练主体或早停集为空，抛出 `ValueError("training period is too small for early stopping")`。

- [ ] **Step 4: 运行测试，确认通过**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_dataset.py -v --basetemp "$env:TEMP\day16-split-green"
```

预期：全部通过。

- [ ] **Step 5: 提交该独立交付物**

```powershell
git add src/ml/dataset.py tests/ml/test_dataset.py
git commit -m "feat: add temporal model selection splits"
```

### Task 2: 训练三类候选并按选择期排名指标选模

**Files:**
- Modify: `src/ml/train.py`
- Modify: `tests/ml/test_evaluate.py`

**Interfaces:**
- Consumes: `training_frame` 和 `early_stopping_frame` 包含 `FEATURE_COLUMNS` 及 `repurchased_within_90d`。
- Produces: `train_candidate_models(training_frame, early_stopping_frame, label_column="repurchased_within_90d") -> dict[str, TrainingResult]`，键固定为 `logistic_regression`、`random_forest`、`lightgbm`。
- Produces: `select_best_candidate(metrics_by_name: dict[str, ModelMetrics]) -> str`，按 `(pr_auc, lift_at_k, name)` 降序选择。
- Produces: `predict_probabilities(result: TrainingResult, frame: pd.DataFrame) -> np.ndarray`，只从 `FEATURE_COLUMNS` 提取列并返回 `[0, 1]` 的正类概率。

- [ ] **Step 1: 写出候选与选择规则的失败测试**

在 `tests/ml/test_evaluate.py` 导入 `ModelMetrics`、`predict_probabilities`、`select_best_candidate` 与 `train_candidate_models`，增加：

```python
def test_select_best_candidate_prioritizes_pr_auc_then_lift():
    metrics = {
        "logistic_regression": ModelMetrics(0.01, 0.03, 0.60, 0.1, 0.02, 0.2, 2.0),
        "random_forest": ModelMetrics(0.01, 0.04, 0.61, 0.1, 0.02, 0.2, 1.5),
        "lightgbm": ModelMetrics(0.01, 0.04, 0.62, 0.1, 0.03, 0.3, 3.0),
    }

    assert select_best_candidate(metrics) == "lightgbm"
```

基于现有 `test_train_candidates_returns_balanced_pipeline_scores` 中的六列 DataFrame，新增包含足够正负例的 `training_frame` 和 `early_stopping_frame`，再断言：

```python
results = train_candidate_models(training_frame, early_stopping_frame)

assert set(results) == {"logistic_regression", "random_forest", "lightgbm"}
assert np.all((0.0 <= predict_probabilities(results["lightgbm"], early_stopping_frame))
              & (predict_probabilities(results["lightgbm"], early_stopping_frame) <= 1.0))
```

- [ ] **Step 2: 运行测试，确认失败**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_evaluate.py -v --basetemp "$env:TEMP\day16-candidates-red"
```

预期：缺少新导出函数导致失败。

- [ ] **Step 3: 实现候选模型与无泄漏的 LightGBM 早停**

保留现有 `FEATURE_COLUMNS` 和 `business_baseline_scores`。将 `TrainingResult.model` 的类型扩宽为 `Any`，以支持 sklearn `Pipeline`；新增以下构造器：

```python
def build_logistic_pipeline() -> Pipeline: ...
def build_random_forest_pipeline() -> Pipeline: ...
def build_lightgbm_pipeline() -> Pipeline: ...
```

三个模型均在 `FEATURE_COLUMNS` 上运行，缺失值用中位数填补。Logistic Regression 继续使用 `StandardScaler()` 和 `class_weight="balanced"`；Random Forest 使用 `RandomForestClassifier(n_estimators=400, min_samples_leaf=20, class_weight="balanced_subsample", n_jobs=-1, random_state=42)`；LightGBM 使用 `LGBMClassifier(objective="binary", learning_rate=0.03, n_estimators=500, num_leaves=15, min_child_samples=50, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", random_state=42, verbosity=-1)`。

`train_candidate_models` 必须：

1. 对训练主体拟合 Logistic Regression 和 Random Forest；
2. 对 LightGBM 先只在 `training_frame` 拟合 preprocessing，再分别转换训练主体与 `early_stopping_frame`；
3. 仅将转换后的 `early_stopping_frame` 传给 `LGBMClassifier.fit(..., eval_set=[...], callbacks=[early_stopping(50, verbose=False)])`；
4. 返回三项 `TrainingResult`，不读取选择期、校准期或最终测试期。

`predict_probabilities` 应调用 `result.model.predict_proba(frame.loc[:, FEATURE_COLUMNS])[:, 1]`，并在返回前检查所有值在 `[0, 1]`；否则抛出 `ValueError("candidate did not return probabilities")`。`select_best_candidate` 使用：

```python
return max(metrics_by_name, key=lambda name: (
    metrics_by_name[name].pr_auc,
    metrics_by_name[name].lift_at_k,
    name,
))
```

- [ ] **Step 4: 运行测试，确认通过并回归 Day 15 行为**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_evaluate.py tests/ml/test_dataset.py -v --basetemp "$env:TEMP\day16-candidates-green"
py -3.13 -m ruff check src/ml tests/ml
```

预期：测试全部通过，Ruff 无问题。

- [ ] **Step 5: 提交该独立交付物**

```powershell
git add src/ml/train.py tests/ml/test_evaluate.py
git commit -m "feat: add boosted repurchase candidates"
```

### Task 3: 用独立时间段校准所选模型并写入可审计产物

**Files:**
- Create: `src/ml/calibration.py`
- Create: `src/ml/artifacts.py`
- Create: `tests/ml/test_calibration.py`
- Create: `tests/ml/test_artifacts.py`

**Interfaces:**
- Produces: `SigmoidCalibrator.fit(raw_probabilities: np.ndarray, labels: np.ndarray) -> SigmoidCalibrator`。
- Produces: `SigmoidCalibrator.predict_proba(raw_probabilities: np.ndarray) -> np.ndarray`。
- Produces: `write_training_artifacts(output_dir: Path, selected_name: str, selected_result: TrainingResult, calibrator: SigmoidCalibrator, metrics: dict[str, object], representative_predictions: pd.DataFrame) -> None`。
- Writes: `artifacts/models/repurchase_pipeline.joblib`、`feature_schema.json`、`metrics.json`、`representative_predictions.json` 和 `model_card.md`。

- [ ] **Step 1: 写出校准与产物的失败测试**

创建 `tests/ml/test_calibration.py`：

```python
def test_sigmoid_calibrator_returns_valid_probabilities():
    calibrator = SigmoidCalibrator().fit(
        np.array([0.05, 0.10, 0.80, 0.95]), np.array([0, 0, 1, 1])
    )

    probabilities = calibrator.predict_proba(np.array([0.10, 0.90]))

    assert np.all((0.0 <= probabilities) & (probabilities <= 1.0))
    assert probabilities[1] > probabilities[0]
```

并增加单类别标签测试：

```python
with pytest.raises(ValueError, match="both classes"):
    SigmoidCalibrator().fit(np.array([0.2, 0.3]), np.array([0, 0]))
```

创建 `tests/ml/test_artifacts.py`：用已拟合的轻量 Logistic Regression `TrainingResult`、已拟合 `SigmoidCalibrator`、两个代表客户行和最小指标字典调用 `write_training_artifacts`，断言五个文件存在；读取 `feature_schema.json`，断言其 `feature_columns` 等于 `list(FEATURE_COLUMNS)`；读取 `metrics.json`，断言其中有 `selected_model` 与 `calibration`。

- [ ] **Step 2: 运行测试，确认失败**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_calibration.py tests/ml/test_artifacts.py -v --basetemp "$env:TEMP\day16-artifacts-red"
```

预期：两个新模块无法导入。

- [ ] **Step 3: 实现 sigmoid 校准与五类产物**

在 `src/ml/calibration.py` 定义：

```python
@dataclass
class SigmoidCalibrator:
    model: LogisticRegression | None = None

    def fit(self, raw_probabilities: np.ndarray, labels: np.ndarray) -> "SigmoidCalibrator": ...
    def predict_proba(self, raw_probabilities: np.ndarray) -> np.ndarray: ...
```

`fit` 将一维原始概率 reshape 为 `(-1, 1)`，使用 `LogisticRegression(random_state=42)` 拟合；先验证等长、非空、数值在 `[0, 1]`、标签同时含 0 和 1。`predict_proba` 在未拟合时抛出 `ValueError("calibrator is not fitted")`，并返回校准器正类概率。

在 `src/ml/artifacts.py` 使用 `joblib.dump` 写出包含 `model`、`calibrator`、`selected_name` 和 `feature_columns` 的单个 `repurchase_pipeline.joblib`。`feature_schema.json` 必须包含：`feature_columns`、每个特征的中文含义、`prediction_time_rule: "首笔已送达订单的送达时间"`、`label_rule: "90天内是否存在后续已送达订单"` 和 `forbidden_future_fields`。`metrics.json` 原样写入传入指标。`representative_predictions.json` 仅写五行代表客户的 `customer_unique_id`、`prediction_time`、六个特征、`raw_probability` 和 `calibrated_probability`。`model_card.md` 必须中文说明：样本、时间切分、选择规则、最终测试指标、非因果限制，以及“特征重要性表示模型关联，不代表因果影响”。

- [ ] **Step 4: 运行测试，确认通过**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_calibration.py tests/ml/test_artifacts.py -v --basetemp "$env:TEMP\day16-artifacts-green"
py -3.13 -m ruff check src/ml tests/ml
```

预期：测试全部通过，Ruff 无问题。

- [ ] **Step 5: 提交该独立交付物**

```powershell
git add src/ml/calibration.py src/ml/artifacts.py tests/ml/test_calibration.py tests/ml/test_artifacts.py
git commit -m "feat: calibrate and persist repurchase model"
```

### Task 4: 编排端到端训练、最终留出评估与学习记录

**Files:**
- Modify: `scripts/train_model.py`
- Modify: `docs/learning/week-2.md`
- Test: `tests/ml/test_evaluate.py`
- Test: `tests/ml/test_dataset.py`
- Test: `tests/ml/test_calibration.py`
- Test: `tests/ml/test_artifacts.py`

**Interfaces:**
- Consumes: `marts.ml_customer_features` 中 `eligible_for_90d` 且标签非空的记录。
- Produces: `artifacts/models/metrics.json`、可加载模型 bundle、schema、模型卡和五个代表客户预测；终端打印选中模型与最终测试 PR-AUC、Lift@10%、Brier score。

- [ ] **Step 1: 写出训练编排的失败测试**

在 `tests/ml/test_artifacts.py` 增加一个针对指标结构的纯函数测试。先在 `scripts/train_model.py` 定义待实现的：

```python
def build_metrics_report(
    candidate_metrics: dict[str, ModelMetrics],
    selected_name: str,
    calibration_before: ModelMetrics,
    calibration_after: ModelMetrics,
    final_test_metrics: ModelMetrics,
) -> dict[str, object]: ...
```

测试断言：`selected_model` 等于传入名称；`candidate_selection` 含所有候选；`calibration` 同时有 `before`、`after`；`final_test` 等于传入最终指标；报告不含任何 `accuracy` 键。

- [ ] **Step 2: 运行测试，确认失败**

运行：

```powershell
py -3.13 -m pytest tests/ml/test_artifacts.py -v --basetemp "$env:TEMP\day16-orchestration-red"
```

预期：无法导入 `build_metrics_report`。

- [ ] **Step 3: 实现端到端时间安全训练流程**

重写 `scripts/train_model.py` 的 `main()`，保持 SQL 条件：

```sql
WHERE eligible_for_90d
  AND repurchased_within_90d IS NOT NULL
ORDER BY prediction_time
```

将三个切点设为 `prediction_time` 的 0.60、0.75、0.80 分位数，并调用 `temporal_four_way_split`。仅对四段中的 `train` 调用 `split_training_for_early_stopping(train, 0.1)`；将前 90% 拟合主体和后 10% 早停主体传给 `train_candidate_models`。

对 `selection`：

1. 用 `evaluate_ranking(labels, business_baseline_scores(selection))` 计算首单金额基线；
2. 用 `evaluate_probabilities` 计算每个候选的 PR-AUC、Lift@10% 与 Brier；
3. 调用 `select_best_candidate`，不能将首单金额基线纳入候选选择。

对 `calibration`：取选中候选的概率，先计算 `calibration_before`，再 `SigmoidCalibrator().fit(raw_scores, labels)`，并用校准后的概率计算 `calibration_after`。只在此处拟合校准器。

对 `test`：仅在候选与校准器完全确定后，计算首单金额规则的 `evaluate_ranking` 和选中模型校准概率的 `evaluate_probabilities`；结果放进 `final_test`。选取校准后的测试分数最高两条、最低两条和中位数一条，构造恰好五条 `representative_predictions`，不得写入非允许的未来字段。

使用 `build_metrics_report` 组织字典：包括时间范围、样本量、患病率、四段样本量、选择期基线、候选选择指标、`selected_model`、校准前后、最终测试的基线及选中模型指标、特征重要性。对于树模型，特征重要性取 `classifier.feature_importances_`；对于 Logistic Regression，取标准化后系数绝对值；将其排序并写入报告。通过 `write_training_artifacts` 写入 `artifacts/models`；控制台明确打印“最终测试集只评估一次”、选中模型和最终测试相对首单金额规则是否提升。

在 `docs/learning/week-2.md` 追加 Day 16 记录：四段时间隔离各自作用；为何 PR-AUC 和 Lift@10% 比 Accuracy 更适合约 1.1% 的复购标签；sigmoid 校准改变概率尺度而不应被用于重新选模；Brier score 的含义；特征重要性不是因果；用实际 `metrics.json` 填入选中模型、最终测试比较和限制。

- [ ] **Step 4: 运行全套验证与真实训练**

运行：

```powershell
py -3.13 -m pytest tests/ml tests/sql -v --basetemp "$env:TEMP\day16-full"
py -3.13 -m ruff check src/ml scripts/train_model.py tests/ml
py -3.13 scripts/train_model.py
```

随后检查 JSON 和模型卡：

```powershell
Get-Content artifacts\models\metrics.json -Raw
Get-Content artifacts\models\model_card.md -Raw
```

预期：所有测试与 Ruff 通过；脚本生成五类产物；`final_test` 同时保留首单金额基线与选中模型结果，即使模型未超过基线也如实记录。

- [ ] **Step 5: 只提交本任务文件并交付结果**

```powershell
git add scripts/train_model.py docs/learning/week-2.md tests/ml/test_artifacts.py
git commit -m "feat: evaluate calibrated boosted repurchase model"
git status --short
```

提交前确认暂存区不含 Global Constraints 中列出的无关改动，也不提交 `artifacts/models/` 的运行结果，除非仓库现有规则明确要求追踪该目录。

## Self-Review

- **Spec coverage:** Task 1 实现训练、选择、校准、测试的严格时间隔离，并把早停限制在训练期。Task 2 训练 LightGBM、Random Forest、Logistic Regression，并以 PR-AUC / Lift@10% 选模。Task 3 实现独立 sigmoid 校准、特征 schema、模型 bundle、校准结果、代表客户与模型卡。Task 4 以未参与选择的最终测试集如实比较模型与首单金额基线，并记录学习结论。
- **Placeholder scan:** 已逐项给出函数签名、测试断言、命令、超参数、文件名和提交范围；不存在未定内容或笼统的后续实现说明。
- **Type consistency:** 四段切分返回 DataFrame；`TrainingResult` 是候选训练、预测与产物持久化共用输入；候选指标使用 `ModelMetrics`；校准器始终接收并输出一维 numpy 概率；`build_metrics_report` 的字典直接供产物写入函数使用。
