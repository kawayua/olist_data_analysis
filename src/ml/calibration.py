"""Probability calibration for the selected repurchase model."""

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class SigmoidCalibrator:
    """Map raw model probabilities to calibration-period probabilities."""

    model: LogisticRegression | None = None

    @staticmethod
    def _probability_array(raw_probabilities: np.ndarray) -> np.ndarray:
        probabilities = np.asarray(raw_probabilities, dtype=float).reshape(-1)
        if len(probabilities) == 0:
            raise ValueError("raw_probabilities must not be empty")
        if not np.all(np.isfinite(probabilities)) or not np.all(
            (0.0 <= probabilities) & (probabilities <= 1.0)
        ):
            raise ValueError("raw_probabilities must be in [0, 1]")
        return probabilities

    def fit(
        self, raw_probabilities: np.ndarray, labels: np.ndarray
    ) -> "SigmoidCalibrator":
        """Fit a sigmoid using a time-isolated calibration period."""
        probabilities = self._probability_array(raw_probabilities)
        calibration_labels = np.asarray(labels).reshape(-1)
        if len(calibration_labels) == 0:
            raise ValueError("labels must not be empty")
        if len(probabilities) != len(calibration_labels):
            raise ValueError("raw_probabilities and labels must have equal length")
        if len(np.unique(calibration_labels)) != 2:
            raise ValueError("labels must contain both classes")

        self.model = LogisticRegression(random_state=42)
        self.model.fit(probabilities.reshape(-1, 1), calibration_labels)
        return self

    def predict_proba(self, raw_probabilities: np.ndarray) -> np.ndarray:
        """Return calibrated positive-class probabilities."""
        if self.model is None:
            raise ValueError("calibrator is not fitted")
        probabilities = self._probability_array(raw_probabilities)
        return self.model.predict_proba(probabilities.reshape(-1, 1))[:, 1]
