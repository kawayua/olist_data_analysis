"""Build and split leakage-safe repurchase training datasets."""

import pandas as pd


def make_repurchase_label(
    prediction_time: pd.Timestamp,
    later_purchases: pd.Series,
    horizon_days: int = 90,
) -> int:
    """Return whether a purchase occurs in the inclusive future horizon."""
    horizon_end = prediction_time + pd.Timedelta(days=horizon_days)
    purchases = pd.to_datetime(later_purchases)
    return int(((purchases > prediction_time) & (purchases <= horizon_end)).any())


def build_training_frame(
    frame: pd.DataFrame,
    data_end: pd.Timestamp,
    horizon_days: int = 90,
) -> pd.DataFrame:
    """Keep only samples with a complete future observation window."""
    result = frame.copy()
    result["prediction_time"] = pd.to_datetime(result["prediction_time"])
    observation_end = result["prediction_time"] + pd.Timedelta(days=horizon_days)
    return result.loc[observation_end <= pd.Timestamp(data_end)].copy()


def temporal_split(
    frame: pd.DataFrame,
    train_end: pd.Timestamp,
    valid_end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split samples into ordered train, validation, and test periods."""
    ordered = frame.copy()
    ordered["prediction_time"] = pd.to_datetime(ordered["prediction_time"])
    ordered = ordered.sort_values("prediction_time")
    train = ordered.loc[ordered["prediction_time"] <= pd.Timestamp(train_end)]
    validation = ordered.loc[
        (ordered["prediction_time"] > pd.Timestamp(train_end))
        & (ordered["prediction_time"] <= pd.Timestamp(valid_end))
    ]
    test = ordered.loc[ordered["prediction_time"] > pd.Timestamp(valid_end)]
    return train.copy(), validation.copy(), test.copy()
