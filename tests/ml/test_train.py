"""Tests for mixed numeric and categorical repurchase features."""

import numpy as np
import pandas as pd

from src.ml.train import FEATURE_COLUMNS, predict_probabilities, train_candidates


def test_training_and_scoring_accept_time_safe_categorical_features():
    """Dropping categories or rejecting a new state would discard usable first-order data."""
    frame = pd.DataFrame(
        {
            **{
                feature: np.arange(12, dtype=float) + index + 1
                for index, feature in enumerate(
                    column for column in FEATURE_COLUMNS
                    if column not in {"customer_state", "first_order_primary_category", "first_order_cross_state", "first_order_is_late"}
                )
            },
            "customer_state": ["SP", "RJ", None] * 4,
            "first_order_primary_category": ["books", "toys", None] * 4,
            "first_order_cross_state": [True, False, True] * 4,
            "first_order_is_late": [False, False, True] * 4,
            "repurchased_within_90d": [False, True] * 6,
        }
    )

    result = train_candidates(frame)
    scoring_frame = frame.drop(columns="repurchased_within_90d").copy()
    scoring_frame.loc[0, "customer_state"] = "AM"

    probabilities = predict_probabilities(result, scoring_frame)

    assert len(probabilities) == len(frame)
    assert np.all((0.0 <= probabilities) & (probabilities <= 1.0))
