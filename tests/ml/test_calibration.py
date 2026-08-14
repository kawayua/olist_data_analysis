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
