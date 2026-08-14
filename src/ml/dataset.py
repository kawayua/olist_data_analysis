"""Build and split leakage-safe repurchase training datasets."""

import math

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


def temporal_four_way_split(
    frame: pd.DataFrame,
    train_end: pd.Timestamp,
    selection_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split samples into ordered train, selection, calibration, and test periods."""
    ordered = frame.copy()
    ordered["prediction_time"] = pd.to_datetime(ordered["prediction_time"])
    ordered = ordered.sort_values("prediction_time")
    train = ordered.loc[ordered["prediction_time"] <= pd.Timestamp(train_end)]
    selection = ordered.loc[
        (ordered["prediction_time"] > pd.Timestamp(train_end))
        & (ordered["prediction_time"] <= pd.Timestamp(selection_end))
    ]
    calibration = ordered.loc[
        (ordered["prediction_time"] > pd.Timestamp(selection_end))
        & (ordered["prediction_time"] <= pd.Timestamp(calibration_end))
    ]
    test = ordered.loc[ordered["prediction_time"] > pd.Timestamp(calibration_end)]
    return train.copy(), selection.copy(), calibration.copy(), test.copy()


def split_training_for_early_stopping(
    train_frame: pd.DataFrame, early_stopping_fraction: float = 0.1
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reserve the latest training samples for early stopping."""
    if not 0 < early_stopping_fraction < 1:
        raise ValueError("early_stopping_fraction must be between 0 and 1")

    ordered = train_frame.copy()
    ordered["prediction_time"] = pd.to_datetime(ordered["prediction_time"])
    ordered = ordered.sort_values("prediction_time")
    early_stopping_size = math.ceil(len(ordered) * early_stopping_fraction)
    fitting = ordered.iloc[:-early_stopping_size]
    early_stopping = ordered.iloc[-early_stopping_size:]
    if fitting.empty or early_stopping.empty:
        raise ValueError("training period is too small for early stopping")
    return fitting.copy(), early_stopping.copy()
