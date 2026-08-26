"""Reproducible synthetic A/B experiments for portfolio-only demonstrations."""

from dataclasses import dataclass
from math import ceil, sqrt

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    seed: int
    treatment_fraction: float
    unit_cost: float
    coupon_cost: float
    average_repurchase_margin: float
    uplift_by_score_decile: tuple[float, ...]

    def __post_init__(self) -> None:
        if not 0 < self.treatment_fraction < 1:
            raise ValueError("treatment_fraction must be in (0, 1)")
        if len(self.uplift_by_score_decile) != 10 or not all(
            0 <= uplift <= 1 for uplift in self.uplift_by_score_decile
        ):
            raise ValueError("uplift_by_score_decile must contain ten values in [0, 1]")
        if min(self.unit_cost, self.coupon_cost, self.average_repurchase_margin) < 0:
            raise ValueError("costs and margin must not be negative")


@dataclass(frozen=True)
class ExperimentRun:
    assignments: pd.DataFrame
    touchpoints: pd.DataFrame
    outcomes_90d: pd.DataFrame
    config: ExperimentConfig


@dataclass(frozen=True)
class ExperimentSummary:
    data_origin: str
    control_customers: int
    treatment_customers: int
    incremental_repurchase_rate: float
    interval_low: float
    interval_high: float
    incremental_margin: float
    total_cost: float
    net_incremental_profit: float
    roi: float | None


def simulate_experiment(customers: pd.DataFrame, config: ExperimentConfig) -> ExperimentRun:
    """Generate deterministic synthetic assignments, touches, and 90-day outcomes."""
    required = {"customer_key", "预测复购概率"}
    if not required <= set(customers):
        raise ValueError("customers must include customer_key and 预测复购概率")
    frame = customers.loc[:, ["customer_key", "预测复购概率"]].copy()
    if frame.empty or not frame["预测复购概率"].between(0, 1).all():
        raise ValueError("customers must contain finite probabilities in [0, 1]")
    frame = frame.sort_values(["预测复购概率", "customer_key"], ascending=[False, True]).reset_index(drop=True)
    frame["score_decile"] = np.clip(
        9 - pd.qcut(frame.index, q=10, labels=False, duplicates="drop").astype(int),
        0,
        9,
    )
    rng = np.random.default_rng(config.seed)
    frame["is_treatment"] = False
    for positions in frame.groupby("score_decile", sort=True).groups.values():
        count = max(1, round(len(positions) * config.treatment_fraction))
        selected = rng.choice(np.asarray(list(positions)), size=count, replace=False)
        frame.loc[selected, "is_treatment"] = True
    frame["arm_name"] = np.where(frame["is_treatment"], "处理组", "对照组")
    frame["data_origin"] = "simulation"
    frame["experiment_name"] = config.name
    frame["assigned_at"] = pd.Timestamp("2018-01-01")
    assignments = frame.copy()
    touchpoints = assignments.loc[:, ["customer_key", "arm_name", "data_origin"]].copy()
    touchpoints["channel"] = config.name
    touchpoints["total_cost"] = np.where(
        touchpoints["arm_name"].eq("处理组"), config.unit_cost + config.coupon_cost, 0.0
    )
    uplift = assignments["score_decile"].map(dict(enumerate(config.uplift_by_score_decile)))
    probability = np.clip(assignments["预测复购概率"] + assignments["is_treatment"] * uplift, 0, 1)
    outcomes = assignments.loc[:, ["customer_key", "arm_name", "score_decile", "data_origin"]].copy()
    outcomes["is_observation_complete"] = True
    outcomes["repurchased_within_90d"] = rng.binomial(1, probability).astype(bool)
    outcomes["incremental_margin"] = outcomes["repurchased_within_90d"].astype(float) * config.average_repurchase_margin
    return ExperimentRun(assignments, touchpoints, outcomes, config)


def summarize_experiment(run: ExperimentRun) -> ExperimentSummary:
    """Compare synthetic treatment and control arms with a normal rate interval."""
    outcomes = run.outcomes_90d
    rates = outcomes.groupby("arm_name")["repurchased_within_90d"].mean()
    counts = outcomes.groupby("arm_name").size()
    control_rate, treatment_rate = rates["对照组"], rates["处理组"]
    difference = float(treatment_rate - control_rate)
    se = sqrt(
        control_rate * (1 - control_rate) / counts["对照组"]
        + treatment_rate * (1 - treatment_rate) / counts["处理组"]
    )
    incremental_margin = difference * counts["处理组"] * run.config.average_repurchase_margin
    total_cost = float(run.touchpoints["total_cost"].sum())
    profit = incremental_margin - total_cost
    return ExperimentSummary(
        "simulation", int(counts["对照组"]), int(counts["处理组"]), difference,
        difference - 1.96 * se, difference + 1.96 * se, incremental_margin,
        total_cost, profit, profit / total_cost if total_cost else None,
    )


def evaluate_contact_thresholds(
    run: ExperimentRun, fractions: tuple[float, ...] = (0.01, 0.03, 0.05, 0.10), risk_floor: float = 0.0
) -> pd.DataFrame:
    """Evaluate economic outcomes for the highest-scored contact fractions."""
    rows = []
    for fraction in fractions:
        keys = (
            run.assignments.sort_values("预测复购概率", ascending=False)
            .groupby("arm_name", group_keys=False)
            .head(max(1, ceil(len(run.assignments) * fraction / 2)))["customer_key"]
        )
        subset = ExperimentRun(
            run.assignments[run.assignments.customer_key.isin(keys)],
            run.touchpoints[run.touchpoints.customer_key.isin(keys)],
            run.outcomes_90d[run.outcomes_90d.customer_key.isin(keys)], run.config,
        )
        summary = summarize_experiment(subset)
        rows.append({"触达比例": fraction, "净增量利润": summary.net_incremental_profit,
                     "区间下界": summary.interval_low, "ROI": summary.roi,
                     "风险通过": summary.interval_low >= risk_floor})
    return pd.DataFrame(rows)


def recommend_threshold(table: pd.DataFrame) -> pd.Series | None:
    """Return the profitable, risk-qualified threshold with the smallest tie-break."""
    eligible = table.loc[table["风险通过"]]
    if eligible.empty:
        return None
    row = eligible.sort_values(["净增量利润", "触达比例"], ascending=[False, True]).iloc[0].copy()
    row["推荐依据"] = "风险线内净增量利润最高"
    return row


def rank_simulated_uplift(run: ExperimentRun) -> pd.DataFrame:
    """Rank synthetic candidates by disclosed uplift assumption and economics."""
    ranked = run.assignments.loc[:, ["customer_key", "score_decile", "data_origin"]].copy()
    ranked["假定绝对提升"] = ranked["score_decile"].map(
        dict(enumerate(run.config.uplift_by_score_decile))
    )
    ranked["预期增量利润"] = (
        ranked["假定绝对提升"] * run.config.average_repurchase_margin
        - run.config.unit_cost
        - run.config.coupon_cost
    )
    return ranked.sort_values(
        ["预期增量利润", "customer_key"], ascending=[False, True]
    ).reset_index(drop=True)
