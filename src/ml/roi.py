"""Budget-constrained marketing ROI scenario calculations."""

from dataclasses import dataclass
from math import floor, isfinite
from numbers import Real

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    """A business assumption for incremental repurchase uplift."""

    name: str
    uplift_rate: float


@dataclass(frozen=True)
class SimulationResult:
    """The incremental financial outcome for one marketing scenario."""

    scenario: str
    contacted_customers: int
    incremental_repurchases: float
    incremental_revenue: float
    marketing_cost: float
    net_incremental_profit: float
    roi: float


def _finite_value(value: float, name: str) -> float:
    """Return a finite numeric value or raise a clear validation error."""
    if not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _validate_scenarios(scenarios: tuple[Scenario, ...]) -> None:
    """Ensure business uplift assumptions are feasible and ordered."""
    if not scenarios:
        raise ValueError("scenarios must not be empty")

    uplift_rates: list[float] = []
    for scenario in scenarios:
        if not isinstance(scenario, Scenario):
            raise TypeError("scenarios must contain Scenario values")
        uplift_rate = _finite_value(scenario.uplift_rate, "uplift_rate")
        if not 0.0 <= uplift_rate <= 1.0:
            raise ValueError("uplift_rate must be in [0, 1]")
        uplift_rates.append(uplift_rate)

    if uplift_rates != sorted(uplift_rates):
        raise ValueError("scenario uplift rates must be in ascending order")


def simulate_roi(
    probabilities: pd.Series,
    budget: float,
    contact_cost: float,
    average_repurchase_revenue: float,
    scenarios: tuple[Scenario, ...],
    max_contact_fraction: float,
) -> list[SimulationResult]:
    """Calculate incremental ROI for the highest-probability customers."""
    _validate_scenarios(scenarios)

    campaign_budget = _finite_value(budget, "budget")
    per_contact_cost = _finite_value(contact_cost, "contact_cost")
    repurchase_revenue = _finite_value(
        average_repurchase_revenue, "average_repurchase_revenue"
    )
    contact_fraction = _finite_value(max_contact_fraction, "max_contact_fraction")
    if campaign_budget <= 0.0:
        raise ValueError("budget must be greater than zero")
    if per_contact_cost <= 0.0:
        raise ValueError("contact_cost must be greater than zero")
    if repurchase_revenue < 0.0:
        raise ValueError("average_repurchase_revenue must not be negative")
    if not 0.0 < contact_fraction <= 1.0:
        raise ValueError("max_contact_fraction must be in (0, 1]")

    probability_values = np.asarray(probabilities, dtype=float).reshape(-1)
    if len(probability_values) == 0:
        raise ValueError("no executable contact plan")
    if not np.all(np.isfinite(probability_values)) or not np.all(
        (0.0 <= probability_values) & (probability_values <= 1.0)
    ):
        raise ValueError("probabilities must be finite values in [0, 1]")

    contacted_customers = min(
        floor(campaign_budget / per_contact_cost),
        floor(len(probability_values) * contact_fraction),
        len(probability_values),
    )
    if contacted_customers == 0:
        raise ValueError("no executable contact plan")

    probability_sum = float(
        np.sort(probability_values)[::-1][:contacted_customers].sum()
    )
    marketing_cost = contacted_customers * per_contact_cost
    results: list[SimulationResult] = []
    for scenario in scenarios:
        incremental_repurchases = round(probability_sum * scenario.uplift_rate, 12)
        incremental_revenue = round(incremental_repurchases * repurchase_revenue, 12)
        net_incremental_profit = round(incremental_revenue - marketing_cost, 12)
        results.append(
            SimulationResult(
                scenario=scenario.name,
                contacted_customers=contacted_customers,
                incremental_repurchases=incremental_repurchases,
                incremental_revenue=incremental_revenue,
                marketing_cost=marketing_cost,
                net_incremental_profit=net_incremental_profit,
                roi=round(net_incremental_profit / marketing_cost, 12),
            )
        )
    return results
