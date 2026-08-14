# Day 15 复购基线与 Logistic Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 比较首单金额业务排序与 Logistic Regression 的 90 天复购客户排序能力。

**Architecture:** `evaluate.py` 只计算模型无关的排序指标；`train.py` 以时间安全训练集拟合业务基线和 Pipeline 内的 Logistic Regression；训练脚本读取集市并写出可审计的 JSON 比较结果。

**Tech Stack:** Python 3.13、pandas、NumPy、scikit-learn、SQLAlchemy、pytest。

## Global Constraints

- 仅使用 Day 14 首单送达时可知的特征。
- 使用按预测时间的训练、验证、测试切分；不随机切分。
- 用 PR-AUC、Precision@K、Recall@K、Lift@K 选择排序方法，Accuracy 不作模型选择依据。
- 所有 Logistic Regression 预处理必须在同一 Pipeline 内。

---

### Task 1: 排序评估函数

**Files:**
- Create: `src/ml/evaluate.py`
- Create: `tests/ml/test_evaluate.py`

**Interfaces:**
- Produces: `lift_at_fraction(y_true, scores, fraction) -> float` 与 `evaluate_probabilities(y_true, probabilities, top_fraction=0.1) -> ModelMetrics`。

- [ ] **Step 1: Write failing tests**

```python
def test_perfect_ranking_has_lift_of_five_at_twenty_percent():
    y_true = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0])
    assert lift_at_fraction(y_true, scores, fraction=0.2) == 5.0

def test_single_class_labels_raise_clear_error():
    with pytest.raises(ValueError, match="both classes"):
        evaluate_probabilities(np.array([0, 0]), np.array([0.2, 0.1]))
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/ml/test_evaluate.py -v`

Expected: FAIL because `evaluate.py` is absent.

- [ ] **Step 3: Implement metrics**

Create an immutable `ModelMetrics` dataclass. Use `average_precision_score`, `roc_auc_score`, `brier_score_loss`; choose `ceil(n * top_fraction)` customers after descending score sort, with at least one customer. Compute precision, recall and Lift as Top-K prevalence divided by full prevalence.

- [ ] **Step 4: Verify GREEN and commit**

Run: `py -3.13 -m pytest tests/ml/test_evaluate.py -v`

Expected: PASS.

Commit: `feat: add ranking evaluation metrics`.

### Task 2: 业务基线与 Logistic Regression

**Files:**
- Create: `src/ml/train.py`
- Modify: `tests/ml/test_evaluate.py`

**Interfaces:**
- Produces: `business_baseline_scores(frame) -> np.ndarray` 与 `train_candidates(training_frame, label_column="repurchased_within_90d") -> TrainingResult`。

- [ ] **Step 1: Write failing tests**

```python
def test_business_baseline_ranks_higher_first_order_value_first():
    scores = business_baseline_scores(pd.DataFrame({"first_order_item_revenue": [10.0, 100.0]}))
    assert scores[1] > scores[0]

def test_train_candidates_returns_pipeline_probability_scores():
    result = train_candidates(sample_training_frame)
    assert result.model.named_steps["classifier"].class_weight == "balanced"
    assert len(result.train_scores) == len(result.train_frame)
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/ml/test_evaluate.py -v`

Expected: FAIL because training functions are absent.

- [ ] **Step 3: Implement candidates**

Business baseline returns `first_order_item_revenue` scores. Build a Pipeline with `ColumnTransformer`, median numerical imputation, `StandardScaler`, and `LogisticRegression(class_weight="balanced", max_iter=1000)`. Exclude audit, label and future-only columns.

- [ ] **Step 4: Verify GREEN and commit**

Run: `py -3.13 -m pytest tests/ml/test_evaluate.py tests/ml/test_dataset.py -v`

Expected: PASS.

Commit: `feat: establish repurchase model baselines`.

### Task 3: 可审计训练脚本与真实数据比较

**Files:**
- Create: `scripts/train_model.py`
- Verify only: `marts.ml_customer_features`

**Interfaces:**
- Produces: `artifacts/models/model_comparison.json`。

- [ ] **Step 1: Write failing artifact test**

```python
def test_model_comparison_includes_time_range_and_metrics(tmp_path):
    write_model_comparison(comparison, tmp_path / "model_comparison.json")
    saved = json.loads((tmp_path / "model_comparison.json").read_text())
    assert {"time_range", "sample_count", "prevalence", "business_baseline", "logistic_regression"} <= saved.keys()
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/ml/test_evaluate.py -v`

Expected: FAIL because the artifact writer is absent.

- [ ] **Step 3: Implement script and writer**

Read `marts.ml_customer_features`, retain `eligible_for_90d` rows, split sequentially into 60% train, 20% validation and 20% test dates, train on train only, evaluate baselines on validation, and write JSON with time range, sample counts, prevalence and metrics. Do not select a final production model on the test partition.

- [ ] **Step 4: Run real comparison in PowerShell**

Run: `py -3.13 scripts/train_model.py`

Expected: `artifacts/models/model_comparison.json` is created; inspect it before any Day 16 modelling decision.

- [ ] **Step 5: Verify and commit**

Run: `py -3.13 -m pytest tests/ml -v`

Expected: PASS.

Commit: `feat: write repurchase model comparison`.
