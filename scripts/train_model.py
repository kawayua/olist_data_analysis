"""Train, calibrate, and audit the Day 16 repurchase model."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database import get_engine
from src.ml.artifacts import FEATURE_MEANINGS, write_training_artifacts
from src.ml.calibration import SigmoidCalibrator
from src.ml.dataset import (
    split_training_for_early_stopping,
    temporal_four_way_split,
)
from src.ml.evaluate import ModelMetrics, evaluate_probabilities, evaluate_ranking
from src.ml.train import (
    FEATURE_COLUMNS,
    business_baseline_scores,
    predict_probabilities,
    select_best_candidate,
    train_candidate_models,
)


def aggregate_feature_importance(
    transformed_names: list[str],
    importances: np.ndarray,
    feature_columns: tuple[str, ...],
) -> dict[str, float]:
    """Aggregate transformed numeric and one-hot weights to source fields."""
    if len(transformed_names) != len(importances):
        raise ValueError("transformed feature names and importances must align")
    totals = {feature: 0.0 for feature in feature_columns}
    for name, importance in zip(transformed_names, importances, strict=True):
        source = name.split("__", 1)[-1]
        matched = next(
            (
                feature
                for feature in feature_columns
                if source == feature or source.startswith(f"{feature}_")
            ),
            None,
        )
        if matched is not None:
            totals[matched] += float(abs(importance))
    return totals


def build_metrics_report(
    candidate_metrics: dict[str, ModelMetrics],
    selected_name: str,
    calibration_before: ModelMetrics,
    calibration_after: ModelMetrics,
    final_test_metrics: ModelMetrics,
) -> dict[str, object]:
    """Build the time-isolated model metric sections without Accuracy."""
    return {
        "candidate_selection": {
            name: metrics.to_dict() for name, metrics in candidate_metrics.items()
        },
        "selected_model": selected_name,
        "calibration": {
            "before": calibration_before.to_dict(),
            "after": calibration_after.to_dict(),
        },
        "final_test": final_test_metrics.to_dict(),
    }


def main() -> None:
    engine = get_engine(get_settings())
    frame = pd.read_sql(
        text(
            """
            SELECT *
            FROM marts.ml_customer_features
            WHERE eligible_for_90d
              AND repurchased_within_90d IS NOT NULL
            ORDER BY prediction_time
            """
        ),
        engine,
    )
    frame["prediction_time"] = pd.to_datetime(frame["prediction_time"])
    train_end = frame["prediction_time"].quantile(0.60)
    selection_end = frame["prediction_time"].quantile(0.75)
    calibration_end = frame["prediction_time"].quantile(0.80)
    train, selection, calibration, test = temporal_four_way_split(
        frame,
        train_end,
        selection_end,
        calibration_end,
    )

    fitting, early_stopping = split_training_for_early_stopping(train, 0.1)
    candidates = train_candidate_models(fitting, early_stopping)

    selection_labels = (
        selection["repurchased_within_90d"].astype(int).to_numpy()
    )
    selection_baseline = evaluate_ranking(
        selection_labels,
        business_baseline_scores(selection),
    )
    candidate_metrics = {
        name: evaluate_probabilities(
            selection_labels,
            predict_probabilities(result, selection),
        )
        for name, result in candidates.items()
    }
    selected_name = select_best_candidate(candidate_metrics)
    selected_result = candidates[selected_name]

    calibration_labels = (
        calibration["repurchased_within_90d"].astype(int).to_numpy()
    )
    calibration_raw_scores = predict_probabilities(selected_result, calibration)
    calibration_before = evaluate_probabilities(
        calibration_labels,
        calibration_raw_scores,
    )
    calibrator = SigmoidCalibrator().fit(
        calibration_raw_scores,
        calibration_labels,
    )
    calibration_after = evaluate_probabilities(
        calibration_labels,
        calibrator.predict_proba(calibration_raw_scores),
    )

    test_labels = test["repurchased_within_90d"].astype(int).to_numpy()
    final_test_baseline = evaluate_ranking(
        test_labels,
        business_baseline_scores(test),
    )
    final_test_raw_scores = predict_probabilities(selected_result, test)
    final_test_calibrated_scores = calibrator.predict_proba(final_test_raw_scores)
    final_test_metrics = evaluate_probabilities(
        test_labels,
        final_test_calibrated_scores,
    )

    if len(test) < 5:
        raise ValueError("final test period must contain at least five samples")
    ranked_positions = np.argsort(final_test_calibrated_scores, kind="stable")
    representative_positions = [
        ranked_positions[-1],
        ranked_positions[-2],
        ranked_positions[0],
        ranked_positions[1],
        ranked_positions[len(ranked_positions) // 2],
    ]
    representative_predictions = test.iloc[representative_positions].copy()
    representative_predictions["raw_probability"] = final_test_raw_scores[
        representative_positions
    ]
    representative_predictions["calibrated_probability"] = (
        final_test_calibrated_scores[representative_positions]
    )

    classifier = selected_result.model.named_steps["classifier"]
    if selected_name == "logistic_regression":
        importances = np.abs(np.asarray(classifier.coef_[0], dtype=float))
    else:
        importances = np.asarray(classifier.feature_importances_, dtype=float)
    transformed_names = list(
        selected_result.model.named_steps["preprocessor"].get_feature_names_out()
    )
    aggregated_importance = aggregate_feature_importance(
        transformed_names, importances, FEATURE_COLUMNS
    )
    feature_importance = sorted(
        (
            {
                "feature": feature,
                "feature_meaning": FEATURE_MEANINGS[feature],
                "importance": importance,
            }
            for feature, importance in aggregated_importance.items()
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )

    metrics = build_metrics_report(
        candidate_metrics,
        selected_name,
        calibration_before,
        calibration_after,
        final_test_metrics,
    )
    metrics.update(
        {
            "time_range": {
                "start": frame["prediction_time"].min().isoformat(),
                "end": frame["prediction_time"].max().isoformat(),
            },
            "sample_count": len(frame),
            "prevalence": float(frame["repurchased_within_90d"].mean()),
            "split_counts": {
                "train": len(train),
                "selection": len(selection),
                "calibration": len(calibration),
                "final_test": len(test),
            },
            "selection_baseline": selection_baseline.to_dict(),
            "feature_importance": feature_importance,
        }
    )
    metrics["final_test"] = {
        "business_baseline": final_test_baseline.to_dict(),
        "selected_model": final_test_metrics.to_dict(),
    }

    output_dir = PROJECT_ROOT / "artifacts" / "models"
    write_training_artifacts(
        output_dir,
        selected_name,
        selected_result,
        calibrator,
        metrics,
        representative_predictions,
    )

    pr_auc_improved = final_test_metrics.pr_auc > final_test_baseline.pr_auc
    lift_improved = final_test_metrics.lift_at_k > final_test_baseline.lift_at_k
    print("最终测试集只评估一次")
    print(f"选中模型：{selected_name}")
    print(
        f"最终测试 PR-AUC：{final_test_metrics.pr_auc:.6f}；"
        f"首单金额规则：{final_test_baseline.pr_auc:.6f}；"
        f"{'提升' if pr_auc_improved else '未提升'}"
    )
    print(
        f"最终测试 Lift@10%：{final_test_metrics.lift_at_k:.6f}；"
        f"首单金额规则：{final_test_baseline.lift_at_k:.6f}；"
        f"{'提升' if lift_improved else '未提升'}"
    )
    print(f"最终测试 Brier score：{final_test_metrics.brier_score:.6f}")
    print(f"已写入 {output_dir.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
