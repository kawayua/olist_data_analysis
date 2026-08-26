"""Tests for reproducible simulated marketing experiments."""

import pandas as pd

from src.ml.experiment import (
    ExperimentConfig,
    evaluate_contact_thresholds,
    rank_simulated_uplift,
    recommend_threshold,
    simulate_experiment,
    summarize_experiment,
)


def _customers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_key": range(100),
            "预测复购概率": [0.02 + index / 10_000 for index in range(100)],
        }
    )


def test_simulation_is_reproducible_and_marks_all_records_as_synthetic():
    """A seed-insensitive run could not be audited or repeated."""
    config = ExperimentConfig(
        name="邮件优惠券", seed=7, treatment_fraction=0.5,
        unit_cost=1.0, coupon_cost=2.0, average_repurchase_margin=80.0,
        uplift_by_score_decile=(0.02,) * 10,
    )

    first = simulate_experiment(_customers(), config)
    second = simulate_experiment(_customers(), config)

    pd.testing.assert_frame_equal(first.assignments, second.assignments)
    pd.testing.assert_frame_equal(first.outcomes_90d, second.outcomes_90d)
    assert first.assignments["data_origin"].eq("simulation").all()
    assert first.outcomes_90d["is_observation_complete"].all()
    assert first.touchpoints.loc[first.touchpoints["arm_name"] == "对照组", "total_cost"].eq(0).all()


def test_threshold_recommendation_uses_profit_then_smaller_fraction():
    """Lift-only ranking can select a smaller but economically inferior campaign."""
    config = ExperimentConfig("邮件", 7, 0.5, 1.0, 0.0, 100.0, (0.2,) * 10)
    run = simulate_experiment(_customers(), config)
    table = evaluate_contact_thresholds(run, risk_floor=-1.0)
    recommendation = recommend_threshold(table)

    assert table["触达比例"].tolist() == [0.01, 0.03, 0.05, 0.1]
    assert recommendation is not None
    assert recommendation["推荐依据"] == "风险线内净增量利润最高"
    assert summarize_experiment(run).data_origin == "simulation"


def test_simulated_uplift_ranks_expected_incremental_profit_not_repurchase_score():
    """A natural-repurchase ranking would select customers who need no treatment."""
    config = ExperimentConfig("邮件", 7, 0.5, 1.0, 0.0, 100.0, (0.01,) * 9 + (0.20,))
    ranked = rank_simulated_uplift(simulate_experiment(_customers(), config))

    assert ranked.iloc[0]["预期增量利润"] == 19.0
    assert ranked["data_origin"].eq("simulation").all()
