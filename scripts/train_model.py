"""Train Day 15 candidates and write validation-set ranking metrics."""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database import get_engine
from src.ml.dataset import temporal_split
from src.ml.evaluate import evaluate_probabilities, evaluate_ranking
from src.ml.train import (
    business_baseline_scores,
    train_candidates,
    write_model_comparison,
)


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
    valid_end = frame["prediction_time"].quantile(0.80)
    train, validation, test = temporal_split(frame, train_end, valid_end)
    result = train_candidates(train)
    labels = validation["repurchased_within_90d"].astype(int).to_numpy()
    baseline_metrics = evaluate_ranking(
        labels, business_baseline_scores(validation)
    )
    logistic_metrics = evaluate_probabilities(
        labels,
        result.model.predict_proba(
            validation.loc[:, result.model.feature_names_in_]
        )[:, 1],
    )
    comparison = {
        "time_range": {
            "start": frame["prediction_time"].min().isoformat(),
            "end": frame["prediction_time"].max().isoformat(),
        },
        "sample_count": len(frame),
        "prevalence": float(frame["repurchased_within_90d"].mean()),
        "split_counts": {
            "train": len(train),
            "validation": len(validation),
            "test_held_out": len(test),
        },
        "business_baseline": baseline_metrics.to_dict(),
        "logistic_regression": logistic_metrics.to_dict(),
    }
    output = PROJECT_ROOT / "artifacts" / "models" / "model_comparison.json"
    write_model_comparison(comparison, output)
    print(f"Wrote {output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
