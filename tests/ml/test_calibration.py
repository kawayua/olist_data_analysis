"""Tests for probability calibration on the held-out calibration period."""

import numpy as np
import pytest

from src.ml.calibration import SigmoidCalibrator


def test_sigmoid_calibrator_maps_higher_raw_score_to_higher_probability():
    """A reversed calibration model must not make high raw scores rank lower."""
    calibrator = SigmoidCalibrator().fit(
        np.array([0.05, 0.10, 0.80, 0.95]), np.array([0, 0, 1, 1])
    )

    probabilities = calibrator.predict_proba(np.array([0.10, 0.90]))

    assert np.all((0.0 <= probabilities) & (probabilities <= 1.0))
    assert probabilities[1] > probabilities[0]


def test_sigmoid_calibrator_rejects_single_class_calibration_labels():
    """Fitting a one-class calibration period would produce an invalid model."""
    with pytest.raises(ValueError, match="both classes"):
        SigmoidCalibrator().fit(np.array([0.1, 0.2]), np.array([0, 0]))


def test_sigmoid_calibrator_rejects_predictions_before_fit():
    """An accidental deploy of an unfitted calibrator must fail loudly."""
    with pytest.raises(ValueError, match="calibrator is not fitted"):
        SigmoidCalibrator().predict_proba(np.array([0.5]))


@pytest.mark.parametrize(
    ("raw_probabilities", "labels", "message"),
    [
        (np.array([]), np.array([]), "raw_probabilities must not be empty"),
        (
            np.array([0.2, 0.8]),
            np.array([0]),
            "raw_probabilities and labels must have equal length",
        ),
        (np.array([0.2, np.nan]), np.array([0, 1]), "raw_probabilities must be in"),
        (np.array([-0.1, 0.8]), np.array([0, 1]), "raw_probabilities must be in"),
        (np.array([0.2, 1.1]), np.array([0, 1]), "raw_probabilities must be in"),
    ],
)
def test_sigmoid_calibrator_rejects_invalid_fit_probabilities(
    raw_probabilities, labels, message
):
    """Calibration must fail before fitting when probability inputs are invalid."""
    with pytest.raises(ValueError, match=message):
        SigmoidCalibrator().fit(raw_probabilities, labels)


@pytest.mark.parametrize(
    "raw_probabilities",
    [np.array([]), np.array([np.inf]), np.array([-0.1]), np.array([1.1])],
)
def test_sigmoid_calibrator_rejects_invalid_prediction_probabilities(raw_probabilities):
    """A fitted calibrator must reject malformed deployment score inputs."""
    calibrator = SigmoidCalibrator().fit(
        np.array([0.05, 0.10, 0.80, 0.95]), np.array([0, 0, 1, 1])
    )

    with pytest.raises(ValueError):
        calibrator.predict_proba(raw_probabilities)
