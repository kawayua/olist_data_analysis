"""Tests for repurchase ranking metrics and baseline candidates."""

import json

import numpy as np
import pandas as pd
import pytest

from src.ml.evaluate import (
    ModelMetrics,
    evaluate_probabilities,
    evaluate_ranking,
    lift_at_fraction,
)
from src.ml.train import (
    business_baseline_scores,
    predict_probabilities,
    select_best_candidate,
    train_candidate_models,
    train_candidates,
    write_model_comparison,
)


def test_perfect_ranking_has_lift_of_five_at_twenty_percent():
    y_true = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0])

    assert lift_at_fraction(y_true, scores, fraction=0.2) == 5.0


def test_evaluate_probabilities_reports_top_k_ranking_metrics():
    metrics = evaluate_probabilities(
        np.array([1, 1, 0, 0, 0]),
        np.array([0.9, 0.8, 0.7, 0.6, 0.5]),
        top_fraction=0.4,
    )

    assert metrics.precision_at_k == 1.0
    assert metrics.recall_at_k == 1.0
    assert metrics.lift_at_k == 2.5


def test_evaluate_ranking_accepts_raw_business_scores_without_brier_score():
    metrics = evaluate_ranking(
        np.array([1, 0, 0]), np.array([4099.99, 100.0, 10.0])
    )

    assert metrics.brier_score is None
    assert metrics.lift_at_k == 3.0


def test_single_class_labels_raise_clear_error():
    with pytest.raises(ValueError, match="both classes"):
        evaluate_probabilities(np.array([0, 0]), np.array([0.2, 0.1]))


def test_business_baseline_ranks_higher_first_order_value_first():
    scores = business_baseline_scores(
        pd.DataFrame({"first_order_item_revenue": [10.0, 100.0]})
    )

    assert scores[1] > scores[0]


def test_train_candidates_returns_balanced_pipeline_scores():
    frame = pd.DataFrame(
        {
            "first_order_item_revenue": [10, 20, 30, 40, 50, 60],
            "first_order_freight_revenue": [1, 2, 3, 4, 5, 6],
            "first_order_payment_value": [11, 22, 33, 44, 55, 66],
            "first_order_item_count": [1, 1, 2, 2, 3, 3],
            "first_order_delivery_days": [2, 3, 4, 5, 6, 7],
            "first_order_distinct_category_count": [1, 1, 2, 1, 2, 2],
            "repurchased_within_90d": [False, False, False, True, True, True],
        }
    )

    result = train_candidates(frame)

    assert result.model.named_steps["classifier"].class_weight == "balanced"
    assert len(result.train_scores) == len(frame)


def test_select_best_candidate_prioritizes_pr_auc_then_lift_at_k():
    baseline_metrics = {
        "prevalence": 0.1,
        "roc_auc": 0.6,
        "brier_score": 0.09,
        "precision_at_k": 0.2,
        "recall_at_k": 0.2,
    }
    metrics_by_name = {
        "logistic_regression": ModelMetrics(
            pr_auc=0.03, lift_at_k=4.0, **baseline_metrics
        ),
        "random_forest": ModelMetrics(
            pr_auc=0.04, lift_at_k=1.5, **baseline_metrics
        ),
        "lightgbm": ModelMetrics(
            pr_auc=0.04, lift_at_k=3.0, **baseline_metrics
        ),
    }

    assert select_best_candidate(metrics_by_name) == "lightgbm"


def test_train_candidate_models_returns_three_candidates_with_probabilities():
    def candidate_frame(start: int, size: int) -> pd.DataFrame:
        sequence = np.arange(start, start + size)
        return pd.DataFrame(
            {
                "first_order_item_count": sequence % 4 + 1,
                "first_order_item_revenue": sequence.astype(float) * 10.0,
                "first_order_freight_revenue": sequence.astype(float) % 7 + 1.0,
                "first_order_payment_value": sequence.astype(float) * 11.0,
                "first_order_delivery_days": sequence.astype(float) % 10 + 1.0,
                "first_order_distinct_category_count": sequence % 3 + 1,
                "repurchased_within_90d": sequence % 2 == 0,
            }
        )

    training_frame = candidate_frame(start=0, size=120)
    early_stopping_frame = candidate_frame(start=120, size=60)

    results = train_candidate_models(training_frame, early_stopping_frame)
    probabilities = predict_probabilities(results["lightgbm"], early_stopping_frame)

    assert set(results) == {"logistic_regression", "random_forest", "lightgbm"}
    assert np.all((0.0 <= probabilities) & (probabilities <= 1.0))


def test_model_comparison_writer_includes_auditable_context(tmp_path):
    path = tmp_path / "model_comparison.json"
    comparison = {
        "time_range": {"start": "2017-01-01", "end": "2018-01-01"},
        "sample_count": 100,
        "prevalence": 0.01,
        "business_baseline": {"lift_at_k": 1.5},
        "logistic_regression": {"lift_at_k": 2.0},
    }

    write_model_comparison(comparison, path)

    assert json.loads(path.read_text(encoding="utf-8")) == comparison
