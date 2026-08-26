"""Model-agnostic ranking metrics for repurchase predictions."""

from dataclasses import asdict, dataclass
from math import ceil

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


@dataclass(frozen=True)
class ModelMetrics:
    """Metrics for a probability-ranked binary classification result."""

    prevalence: float
    pr_auc: float
    roc_auc: float
    brier_score: float | None
    precision_at_k: float
    recall_at_k: float
    lift_at_k: float

    def to_dict(self) -> dict[str, float | None]:
        """Return serializable metric names and values."""
        return asdict(self)


def _validate_binary_inputs(y_true: np.ndarray, scores: np.ndarray) -> None:
    if len(y_true) == 0:
        raise ValueError("y_true must not be empty")
    if len(y_true) != len(scores):
        raise ValueError("y_true and scores must have equal length")
    if len(np.unique(y_true)) != 2:
        raise ValueError("y_true must contain both classes")


def lift_at_fraction(
    y_true: np.ndarray, scores: np.ndarray, fraction: float
) -> float:
    """Return Top-K prevalence divided by the full-sample prevalence."""
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    _validate_binary_inputs(y_true, scores)
    top_count = max(1, ceil(len(y_true) * fraction))
    ordered = np.argsort(-scores, kind="stable")[:top_count]
    prevalence = float(np.mean(y_true))
    return float(np.mean(y_true[ordered]) / prevalence)


def _evaluate_scores(
    labels: np.ndarray,
    scores: np.ndarray,
    top_fraction: float,
    brier_score: float | None,
) -> ModelMetrics:
    top_count = max(1, ceil(len(labels) * top_fraction))
    ordered = np.argsort(-scores, kind="stable")[:top_count]
    positives_at_k = float(labels[ordered].sum())
    prevalence = float(labels.mean())
    precision_at_k = positives_at_k / top_count
    return ModelMetrics(
        prevalence=prevalence,
        pr_auc=float(average_precision_score(labels, scores)),
        roc_auc=float(roc_auc_score(labels, scores)),
        brier_score=brier_score,
        precision_at_k=precision_at_k,
        recall_at_k=positives_at_k / float(labels.sum()),
        lift_at_k=precision_at_k / prevalence,
    )


def evaluate_ranking(
    y_true: np.ndarray, scores: np.ndarray, top_fraction: float = 0.1
) -> ModelMetrics:
    """Evaluate raw ranking scores without treating them as probabilities."""
    labels = np.asarray(y_true, dtype=int)
    ranking_scores = np.asarray(scores, dtype=float)
    _validate_binary_inputs(labels, ranking_scores)
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    return _evaluate_scores(labels, ranking_scores, top_fraction, brier_score=None)


def evaluate_probabilities(
    y_true: np.ndarray, probabilities: np.ndarray, top_fraction: float = 0.1
) -> ModelMetrics:
    """Calculate ranking and calibration metrics from predicted probabilities."""
    labels = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    _validate_binary_inputs(labels, scores)
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    return _evaluate_scores(
        labels,
        scores,
        top_fraction,
        brier_score=float(brier_score_loss(labels, scores)),
    )


def evaluate_at_fractions(
    y_true: np.ndarray,
    scores: np.ndarray,
    fractions: tuple[float, ...] = (0.01, 0.03, 0.05, 0.10),
) -> dict[str, ModelMetrics]:
    """Evaluate a ranking at the campaign contact ranges shown to users."""
    return {
        f"{fraction:.0%}": evaluate_ranking(y_true, scores, top_fraction=fraction)
        for fraction in fractions
    }
