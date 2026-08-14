"""Tests for budget-constrained marketing ROI scenarios."""

import pandas as pd
import pytest

from src.ml.roi import (
    Scenario,
    recommend_profit_maximizing_plan,
    simulate_roi,
)


def test_simulator_calculates_incremental_profit_for_top_customers():
    """A missing incremental-uplift calculation would understate campaign profit."""
    results = simulate_roi(
        pd.Series([0.8, 0.4, 0.1]),
        20,
        10,
        100,
        (Scenario("基准", 0.1),),
        1.0,
    )

    result = results[0]

    assert result.contacted_customers == 2
    assert result.incremental_repurchases == 0.12
    assert result.incremental_revenue == 12.0
    assert result.marketing_cost == 20.0
    assert result.net_incremental_profit == -8.0
    assert result.roi == -0.4


def test_simulator_spends_budget_on_highest_probability_customers_only():
    """A missing probability sort would contact low-value customers first."""
    result = simulate_roi(
        pd.Series([0.2, 0.1, 0.9]),
        20,
        10,
        100,
        (Scenario("基准", 0.5),),
        1.0,
    )[0]

    assert result.contacted_customers == 2
    assert result.incremental_repurchases == 0.55


def test_simulator_limits_contacts_to_budget_capacity():
    """An ignored budget constraint would overstate the executable audience."""
    result = simulate_roi(
        pd.Series([0.9, 0.8, 0.7]),
        19,
        10,
        100,
        (Scenario("基准", 0.1),),
        1.0,
    )[0]

    assert result.contacted_customers == 1
    assert result.marketing_cost == 10.0


def test_simulator_limits_contacts_to_maximum_contact_fraction():
    """An ignored contact-fraction cap would overstate the executable audience."""
    result = simulate_roi(
        pd.Series([0.9, 0.8, 0.7, 0.6, 0.5]),
        1_000,
        10,
        100,
        (Scenario("基准", 0.1),),
        0.4,
    )[0]

    assert result.contacted_customers == 2
    assert result.marketing_cost == 20.0


def test_simulator_higher_uplift_produces_higher_profit():
    """An uplift-independent formula would make optimistic plans no better."""
    results = simulate_roi(
        pd.Series([0.8, 0.4]),
        20,
        10,
        100,
        (Scenario("保守", 0.1), Scenario("乐观", 0.3)),
        1.0,
    )

    assert results[1].net_incremental_profit > results[0].net_incremental_profit


@pytest.mark.parametrize(
    ("budget", "contact_cost", "average_repurchase_revenue"),
    [(-1, 10, 100), (20, 0, 100), (20, 10, -1)],
)
def test_simulator_rejects_invalid_financial_inputs(
    budget, contact_cost, average_repurchase_revenue
):
    """Invalid campaign economics must fail before calculating a result."""
    with pytest.raises(ValueError):
        simulate_roi(
            pd.Series([0.8]),
            budget,
            contact_cost,
            average_repurchase_revenue,
            (Scenario("基准", 0.1),),
            1.0,
        )


@pytest.mark.parametrize(
    "scenarios",
    [
        (Scenario("基准", -0.1),),
        (Scenario("基准", 1.1),),
        (Scenario("基准", 0.3), Scenario("保守", 0.1)),
    ],
)
def test_simulator_rejects_invalid_or_unsorted_uplifts(scenarios):
    """Invalid scenario assumptions must not silently create a misleading plan."""
    with pytest.raises(ValueError):
        simulate_roi(pd.Series([0.8]), 10, 10, 100, scenarios, 1.0)


def test_simulator_rejects_budget_that_cannot_cover_one_contact():
    """A zero-customer plan must not be presented as an executable campaign."""
    with pytest.raises(ValueError, match="no executable contact plan"):
        simulate_roi(
            pd.Series([0.8]),
            9,
            10,
            100,
            (Scenario("基准", 0.1),),
            1.0,
        )


def test_recommendation_uses_net_incremental_profit_not_roi():
    """An ROI-only ranking would incorrectly prefer the smallest budget."""
    result = recommend_profit_maximizing_plan(
        pd.Series([0.9, 0.8, 0.7]),
        (10, 20, 30),
        10,
        100,
        Scenario("基准", 0.5),
        1.0,
    )

    assert result.contacted_customers == 3
