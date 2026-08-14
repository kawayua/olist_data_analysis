"""Tests for auditable repurchase-model artifact persistence."""

import json

import joblib
import numpy as np
import pandas as pd

from src.ml.artifacts import write_training_artifacts
from src.ml.calibration import SigmoidCalibrator
from src.ml.train import FEATURE_COLUMNS, train_candidates


def _small_training_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "first_order_item_count": [1, 1, 2, 2, 3, 3],
            "first_order_item_revenue": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "first_order_freight_revenue": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "first_order_payment_value": [11.0, 22.0, 33.0, 44.0, 55.0, 66.0],
            "first_order_delivery_days": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "first_order_distinct_category_count": [1, 1, 2, 1, 2, 2],
            "repurchased_within_90d": [False, False, False, True, True, True],
        }
    )


def test_writer_persists_model_schema_metrics_and_safe_representative_rows(tmp_path):
    """Persisted evidence must retain audit inputs without retaining future labels."""
    selected_result = train_candidates(_small_training_frame())
    calibrator = SigmoidCalibrator().fit(
        np.array([0.05, 0.10, 0.80, 0.95]), np.array([0, 0, 1, 1])
    )
    metrics = {
        "selected_model": "logistic_regression",
        "calibration": {"brier_score": 0.12},
        "final_test": {"pr_auc": 0.31},
    }
    representative_predictions = pd.DataFrame(
        {
            "customer_unique_id": ["customer-1", "customer-2"],
            "prediction_time": ["2018-01-01", "2018-01-02"],
            **{
                feature: [float(index + 1), float(index + 2)]
                for index, feature in enumerate(FEATURE_COLUMNS)
            },
            "raw_probability": [0.2, 0.8],
            "calibrated_probability": [0.1, 0.9],
            "repurchased_within_90d": [0, 1],
        }
    )

    write_training_artifacts(
        tmp_path,
        "logistic_regression",
        selected_result,
        calibrator,
        metrics,
        representative_predictions,
    )

    assert {
        path.name for path in tmp_path.iterdir()
    } == {
        "repurchase_pipeline.joblib",
        "feature_schema.json",
        "metrics.json",
        "representative_predictions.json",
        "model_card.md",
    }
    pipeline = joblib.load(tmp_path / "repurchase_pipeline.joblib")
    assert pipeline["selected_name"] == "logistic_regression"
    assert pipeline["feature_columns"] == list(FEATURE_COLUMNS)

    schema = json.loads((tmp_path / "feature_schema.json").read_text(encoding="utf-8"))
    assert schema["feature_columns"] == list(FEATURE_COLUMNS)
    assert set(schema["feature_meanings"]) == set(FEATURE_COLUMNS)
    assert "prediction_time_rule" in schema
    assert "label_rule" in schema
    assert schema["forbidden_future_fields"]

    assert json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8")) == metrics
    rows = json.loads(
        (tmp_path / "representative_predictions.json").read_text(encoding="utf-8")
    )
    assert len(rows) == 2
    assert "repurchased_within_90d" not in rows[0]
    assert set(rows[0]).issubset(
        {
            "customer_unique_id",
            "order_id",
            "customer_id",
            "prediction_time",
            *FEATURE_COLUMNS,
            "raw_probability",
            "calibrated_probability",
        }
    )
    model_card = (tmp_path / "model_card.md").read_text(encoding="utf-8")
    assert "特征重要性反映关联而非因果关系" in model_card
