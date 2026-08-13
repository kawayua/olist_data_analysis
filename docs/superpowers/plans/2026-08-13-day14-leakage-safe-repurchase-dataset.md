# Day 14 时间安全复购训练集 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一个以首单送达时点预测未来 90 天复购的无泄漏训练集。

**Architecture:** SQL 以客户首单送达为粒度，产生仅在该时点可知的特征、90 天标签和观察期资格；Python 过滤可训练样本并按时间切分。

**Tech Stack:** PostgreSQL、Python 3.13、pandas、pytest、SQLAlchemy。

## Global Constraints

- 不使用预测时点之后才产生的订单、累计消费、最终 RFM 或评分。
- 标签窗口为 `(prediction_time, prediction_time + 90 days]`。
- 不完整观察期样本不得进入训练、验证或测试集。
- 时间切分必须满足训练 < 验证 < 测试。

---

### Task 1: 用失败测试定义标签与时间切分

**Files:**
- Create: `src/ml/__init__.py`
- Create: `src/ml/dataset.py`
- Create: `tests/ml/test_dataset.py`

**Interfaces:**
- Produces: `make_repurchase_label(prediction_time, later_purchases, horizon_days=90) -> int`、`build_training_frame(frame, data_end, horizon_days=90) -> pd.DataFrame`、`temporal_split(frame, train_end, valid_end) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]`。

- [ ] **Step 1: Write failing tests**

```python
def test_purchase_inside_90_days_is_positive():
    assert make_repurchase_label(pd.Timestamp("2018-01-01"), pd.Series(pd.to_datetime(["2018-03-15"])), 90) == 1

def test_purchase_after_90_days_is_negative():
    assert make_repurchase_label(pd.Timestamp("2018-01-01"), pd.Series(pd.to_datetime(["2018-05-01"])), 90) == 0

def test_training_frame_excludes_incomplete_observation_window():
    frame = pd.DataFrame({"prediction_time": pd.to_datetime(["2018-01-01", "2018-11-01"]), "repurchased_within_90d": [True, False]})
    result = build_training_frame(frame, pd.Timestamp("2018-12-01"))
    assert result.prediction_time.tolist() == [pd.Timestamp("2018-01-01")]
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/ml/test_dataset.py -v`

Expected: FAIL because the ML package and functions do not yet exist.

- [ ] **Step 3: Implement minimal Python dataset functions**

Use an inclusive horizon end, filter `prediction_time + horizon_days <= data_end`, and split with `prediction_time <= train_end`, then `<= valid_end`, then remaining later rows.

- [ ] **Step 4: Verify GREEN and commit**

Run: `py -3.13 -m pytest tests/ml/test_dataset.py -v`

Expected: PASS.

Commit: `feat: build leakage-safe repurchase dataset utilities`.

### Task 2: 新建首单送达时点 SQL 集市

**Files:**
- Create: `sql/marts/035_ml_customer_features.sql`
- Modify: `tests/sql/test_customer_value_repurchases.py`

**Interfaces:**
- Produces: `marts.ml_customer_features`，一客户一行，含 `prediction_time`、`feature_available_at`、首单可知特征、`eligible_for_90d` 与 `repurchased_within_90d`。

- [ ] **Step 1: Write failing SQL contract test**

```python
def test_ml_customer_features_exposes_prediction_audit_columns(engine):
    columns = set(pd.read_sql("SELECT * FROM marts.ml_customer_features LIMIT 0", engine).columns)
    assert {"customer_key", "prediction_time", "feature_available_at", "eligible_for_90d", "repurchased_within_90d"} <= columns
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/sql/test_customer_value_repurchases.py -v`

Expected: FAIL because the mart does not yet exist.

- [ ] **Step 3: Implement mart SQL**

Aggregate first delivered order and its items; retain only first-order attributes. Join later delivered orders only to form the label; calculate eligibility from the maximum delivered timestamp. Do not join reviews or `customer_360`.

- [ ] **Step 4: Execute SQL in Navicat and verify GREEN**

Run the file in Navicat, then: `py -3.13 -m pytest tests/sql/test_customer_value_repurchases.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add leakage-safe customer feature mart`.

### Task 3: 验证真实训练样本

**Files:**
- Verify only: `src/ml/dataset.py`
- Verify only: `sql/marts/035_ml_customer_features.sql`

- [ ] **Step 1: Query counts in Navicat**

```sql
SELECT eligible_for_90d, COUNT(*) AS customer_count,
       AVG(repurchased_within_90d::int) AS repurchase_rate
FROM marts.ml_customer_features
GROUP BY eligible_for_90d;
```

- [ ] **Step 2: Run ML and SQL tests**

Run: `py -3.13 -m pytest tests/ml tests/sql -v --basetemp "$env:TEMP\\day14-ml"`

Expected: PASS.
