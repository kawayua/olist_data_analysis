"""Tests for repurchase ranking metrics and baseline candidates."""

import numpy as np
import pytest

from src.ml.evaluate import evaluate_probabilities, lift_at_fraction


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


def test_single_class_labels_raise_clear_error():
    with pytest.raises(ValueError, match="both classes"):
        evaluate_probabilities(np.array([0, 0]), np.array([0.2, 0.1]))
