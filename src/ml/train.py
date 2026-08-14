"""Baseline and Logistic Regression candidates for repurchase ranking."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = (
    "first_order_item_count",
    "first_order_item_revenue",
    "first_order_freight_revenue",
    "first_order_payment_value",
    "first_order_delivery_days",
    "first_order_distinct_category_count",
)


@dataclass(frozen=True)
class TrainingResult:
    """A fitted candidate and its in-sample probability scores."""

    model: Pipeline
    train_frame: pd.DataFrame
    train_scores: np.ndarray


def business_baseline_scores(frame: pd.DataFrame) -> np.ndarray:
    """Score customers by first-order item revenue for a simple rule baseline."""
    return frame["first_order_item_revenue"].fillna(0.0).to_numpy(dtype=float)


def train_candidates(
    training_frame: pd.DataFrame,
    label_column: str = "repurchased_within_90d",
) -> TrainingResult:
    """Fit a balanced Logistic Regression using only time-safe numerical features."""
    missing_features = set(FEATURE_COLUMNS).difference(training_frame.columns)
    if missing_features:
        raise ValueError(f"missing required features: {sorted(missing_features)}")
    if label_column not in training_frame:
        raise ValueError(f"missing label column: {label_column}")

    frame = training_frame.dropna(subset=[label_column]).copy()
    labels = frame[label_column].astype(int)
    preprocessor = ColumnTransformer(
        [("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), list(FEATURE_COLUMNS))],
        remainder="drop",
    )
    model = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(class_weight="balanced", max_iter=1000),
            ),
        ]
    )
    model.fit(frame.loc[:, FEATURE_COLUMNS], labels)
    scores = model.predict_proba(frame.loc[:, FEATURE_COLUMNS])[:, 1]
    return TrainingResult(model=model, train_frame=frame, train_scores=scores)


def write_model_comparison(comparison: dict[str, object], path: Path) -> None:
    """Write an auditable model comparison artifact as UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
