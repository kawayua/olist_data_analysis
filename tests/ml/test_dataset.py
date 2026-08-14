"""Tests for time-safe repurchase training data."""

import pandas as pd

from src.ml.dataset import (
    build_training_frame,
    make_repurchase_label,
    split_training_for_early_stopping,
    temporal_four_way_split,
    temporal_split,
)


def test_purchase_inside_90_days_is_positive():
    prediction_time = pd.Timestamp("2018-01-01")
    purchases = pd.Series(pd.to_datetime(["2018-03-15"]))

    assert make_repurchase_label(prediction_time, purchases, 90) == 1


def test_purchase_after_90_days_is_negative():
    prediction_time = pd.Timestamp("2018-01-01")
    purchases = pd.Series(pd.to_datetime(["2018-05-01"]))

    assert make_repurchase_label(prediction_time, purchases, 90) == 0


def test_training_frame_excludes_incomplete_observation_window():
    frame = pd.DataFrame(
        {
            "prediction_time": pd.to_datetime(["2018-01-01", "2018-11-01"]),
            "repurchased_within_90d": [True, False],
        }
    )

    result = build_training_frame(frame, pd.Timestamp("2018-12-01"))

    assert result.prediction_time.tolist() == [pd.Timestamp("2018-01-01")]


def test_temporal_split_keeps_time_ranges_strictly_ordered():
    frame = pd.DataFrame(
        {"prediction_time": pd.to_datetime(["2018-01-01", "2018-04-01", "2018-07-01"])}
    )

    train, validation, test = temporal_split(
        frame, pd.Timestamp("2018-02-01"), pd.Timestamp("2018-05-01")
    )

    assert train.prediction_time.max() < validation.prediction_time.min()
    assert validation.prediction_time.max() < test.prediction_time.min()


def test_temporal_four_way_split_keeps_time_ranges_strictly_ordered():
    frame = pd.DataFrame(
        {
            "prediction_time": pd.to_datetime(
                [
                    "2018-01-01",
                    "2018-02-01",
                    "2018-03-01",
                    "2018-04-01",
                    "2018-05-01",
                    "2018-06-01",
                    "2018-07-01",
                    "2018-08-01",
                ]
            )
        }
    )

    train, selection, calibration, test = temporal_four_way_split(
        frame,
        pd.Timestamp("2018-02-15"),
        pd.Timestamp("2018-04-15"),
        pd.Timestamp("2018-06-15"),
    )

    assert train.prediction_time.max() < selection.prediction_time.min()
    assert selection.prediction_time.max() < calibration.prediction_time.min()
    assert calibration.prediction_time.max() < test.prediction_time.min()


def test_split_training_for_early_stopping_reserves_latest_rows():
    frame = pd.DataFrame(
        {"prediction_time": pd.date_range("2018-01-01", periods=10, freq="D")}
    )

    fitting, early_stopping = split_training_for_early_stopping(frame, 0.2)

    assert len(fitting) == 8
    assert len(early_stopping) == 2
    assert fitting.prediction_time.max() < early_stopping.prediction_time.min()
