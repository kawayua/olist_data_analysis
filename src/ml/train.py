"""Baseline, logistic regression, random forest, and LightGBM repurchase candidates."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, early_stopping
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.ml.evaluate import ModelMetrics

NUMERIC_FEATURE_COLUMNS = (
    "first_order_item_count",
    "first_order_item_revenue",
    "first_order_freight_revenue",
    "first_order_payment_value",
    "first_order_delivery_days",
    "first_order_distinct_category_count",
    "first_order_max_item_revenue",
    "first_order_average_item_revenue",
    "first_order_freight_rate",
    "first_order_payment_type_count",
    "first_order_max_installments",
    "first_order_seller_state_count",
    "first_order_estimated_delivery_days",
    "first_order_delivery_vs_estimate_days",
    "first_order_purchase_month",
    "first_order_purchase_weekday",
    "first_order_approval_hours",
    "first_order_carrier_handoff_hours",
)

CATEGORICAL_FEATURE_COLUMNS = (
    "customer_state",
    "first_order_primary_category",
    "first_order_cross_state",
    "first_order_is_late",
)

FEATURE_COLUMNS = (*NUMERIC_FEATURE_COLUMNS, *CATEGORICAL_FEATURE_COLUMNS)


@dataclass(frozen=True)
class TrainingResult:
    """A fitted candidate and its in-sample probability scores."""

    model: Pipeline
    train_frame: pd.DataFrame
    train_scores: np.ndarray


def _numeric_preprocessor(include_scaler: bool = False) -> ColumnTransformer:
    steps = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if include_scaler:
        steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        [
            ("numeric", Pipeline(steps), list(NUMERIC_FEATURE_COLUMNS)),
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="most_frequent", keep_empty_features=True
                            ),
                        ),
                        (
                            "encoder",
                            OneHotEncoder(
                                handle_unknown="ignore", sparse_output=False
                            ),
                        ),
                    ]
                ),
                list(CATEGORICAL_FEATURE_COLUMNS),
            ),
        ],
        remainder="drop",
    )


def _feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the complete model contract, leaving absent fields as imputable nulls."""
    return frame.reindex(columns=FEATURE_COLUMNS)


def build_logistic_pipeline() -> Pipeline:
    """Build the balanced logistic-regression candidate pipeline."""
    return Pipeline(
        [
            ("preprocessor", _numeric_preprocessor(include_scaler=True)),
            (
                "classifier",
                LogisticRegression(class_weight="balanced", max_iter=1000),
            ),
        ]
    )


def build_random_forest_pipeline() -> Pipeline:
    """Build the balanced random-forest candidate pipeline."""
    return Pipeline(
        [
            ("preprocessor", _numeric_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=400,
                    min_samples_leaf=20,
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                    random_state=42,
                ),
            ),
        ]
    )


def build_lightgbm_pipeline() -> Pipeline:
    """Build the LightGBM candidate pipeline with leakage-safe preprocessing."""
    preprocessor = _numeric_preprocessor().set_output(transform="pandas")
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LGBMClassifier(
                    objective="binary",
                    learning_rate=0.03,
                    n_estimators=500,
                    num_leaves=15,
                    min_child_samples=50,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    class_weight="balanced",
                    random_state=42,
                    verbosity=-1,
                ),
            ),
        ]
    )


def _validate_training_frame(frame: pd.DataFrame, label_column: str) -> pd.DataFrame:
    if label_column not in frame:
        raise ValueError(f"missing label column: {label_column}")
    return frame.dropna(subset=[label_column]).copy()


def business_baseline_scores(frame: pd.DataFrame) -> np.ndarray:
    """Score customers by first-order item revenue for a simple rule baseline."""
    return frame["first_order_item_revenue"].fillna(0.0).to_numpy(dtype=float)


def train_candidates(
    training_frame: pd.DataFrame,
    label_column: str = "repurchased_within_90d",
) -> TrainingResult:
    """Fit a balanced Logistic Regression using only time-safe numerical features."""
    frame = _validate_training_frame(training_frame, label_column)
    labels = frame[label_column].astype(int)
    model = build_logistic_pipeline()
    features = _feature_frame(frame)
    model.fit(features, labels)
    scores = model.predict_proba(features)[:, 1]
    return TrainingResult(model=model, train_frame=frame, train_scores=scores)


def train_candidate_models(
    training_frame: pd.DataFrame,
    early_stopping_frame: pd.DataFrame,
    label_column: str = "repurchased_within_90d",
) -> dict[str, TrainingResult]:
    """Fit ranking candidates using only training data and early stopping data."""
    fitting_frame = _validate_training_frame(training_frame, label_column)
    stopping_frame = _validate_training_frame(early_stopping_frame, label_column)
    fitting_labels = fitting_frame[label_column].astype(int)
    stopping_labels = stopping_frame[label_column].astype(int)
    fitting_features = _feature_frame(fitting_frame)

    results: dict[str, TrainingResult] = {}
    for name, model in {
        "logistic_regression": build_logistic_pipeline(),
        "random_forest": build_random_forest_pipeline(),
    }.items():
        model.fit(fitting_features, fitting_labels)
        results[name] = TrainingResult(
            model=model,
            train_frame=fitting_frame,
            train_scores=model.predict_proba(fitting_features)[:, 1],
        )

    lightgbm_model = build_lightgbm_pipeline()
    preprocessor = lightgbm_model.named_steps["preprocessor"]
    classifier = lightgbm_model.named_steps["classifier"]
    transformed_fitting_features = preprocessor.fit_transform(fitting_features)
    transformed_stopping_features = preprocessor.transform(_feature_frame(stopping_frame))
    classifier.fit(
        transformed_fitting_features,
        fitting_labels,
        eval_set=[(transformed_stopping_features, stopping_labels)],
        callbacks=[early_stopping(50, verbose=False)],
    )
    results["lightgbm"] = TrainingResult(
        model=lightgbm_model,
        train_frame=fitting_frame,
        train_scores=lightgbm_model.predict_proba(fitting_features)[:, 1],
    )
    return results


def predict_probabilities(result: TrainingResult, frame: pd.DataFrame) -> np.ndarray:
    """Return validated positive-class candidate probabilities for feature inputs."""
    probabilities = np.asarray(
        result.model.predict_proba(_feature_frame(frame))[:, 1], dtype=float
    )
    if not np.all((0.0 <= probabilities) & (probabilities <= 1.0)):
        raise ValueError("candidate did not return probabilities")
    return probabilities


def select_best_candidate(metrics_by_name: dict[str, ModelMetrics]) -> str:
    """Return the candidate with the best PR-AUC, Lift@10%, then name."""
    return max(metrics_by_name, key=lambda name: (
        metrics_by_name[name].pr_auc,
        metrics_by_name[name].lift_at_k,
        name,
    ))


def write_model_comparison(comparison: dict[str, object], path: Path) -> None:
    """Write an auditable model comparison artifact as UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
