"""Governed analysis tools for the Day 18 agent boundary."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import Any, Protocol

import joblib
import pandas as pd
import plotly.express as px
from sqlalchemy import text

from src.agent.client import ToolDefinition
from src.agent.safety import validate_read_only_sql
from src.analytics.metrics import get_metric_definition
from src.ml.roi import Scenario, SimulationResult, simulate_roi
from src.ml.train import FEATURE_COLUMNS


class ReadOnlyQueryExecutor(Protocol):
    """Execute an already validated analytical query without write privileges."""

    def read_only_query(self, sql: str) -> pd.DataFrame:
        """Return rows for one validated read-only query."""


class SQLAlchemyReadOnlyExecutor:
    """Production executor with an independent database read-only boundary."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def read_only_query(self, sql: str) -> pd.DataFrame:
        """Run a validated query inside a short-lived read-only transaction."""
        with self._engine.begin() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            return pd.read_sql_query(text(sql), connection).head(2_000)


Predictor = Callable[[pd.DataFrame], float]
CampaignSimulator = Callable[..., list[SimulationResult]]


def _artifact_predictor(feature_frame: pd.DataFrame) -> float:
    """Score one feature row using the saved, calibrated model artifact."""
    artifact_path = (
        Path(__file__).resolve().parents[2]
        / "artifacts"
        / "models"
        / "repurchase_pipeline.joblib"
    )
    bundle = joblib.load(artifact_path)
    if tuple(bundle.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise ValueError("saved model feature schema is incompatible")
    raw_probability = bundle["model"].predict_proba(feature_frame)[:, 1]
    calibrated_probability = bundle["calibrator"].predict_proba(raw_probability)[0]
    return float(calibrated_probability)


class AnalysisTools:
    """The future agent's single registry for governed project capabilities."""

    def __init__(
        self,
        executor: ReadOnlyQueryExecutor,
        allowed_views: set[str],
        predictor: Predictor | None = None,
        campaign_simulator: CampaignSimulator = simulate_roi,
    ) -> None:
        self._executor = executor
        self._allowed_views = frozenset(allowed_views)
        self._predictor = predictor or _artifact_predictor
        self._campaign_simulator = campaign_simulator

    def run_safe_sql(self, sql: str) -> dict[str, object]:
        """Validate SQL before execution and serialize no more than 2,000 rows."""
        normalized_sql = validate_read_only_sql(sql, self._allowed_views)
        frame = self._executor.read_only_query(normalized_sql)
        return {
            "sql": normalized_sql,
            "rows": _json_safe_records(frame.head(2_000)),
        }

    def get_metric_definition(self, name: str) -> dict[str, str]:
        """Return a governed metric contract, not an ad-hoc calculation."""
        return asdict(get_metric_definition(name))

    def create_chart(
        self,
        chart_type: str,
        data: Sequence[dict[str, Any]],
        x: str,
        y: str,
    ) -> dict[str, Any]:
        """Create one bounded Plotly chart from explicit record fields only."""
        if chart_type not in {"bar", "line", "scatter"}:
            raise ValueError("unsupported chart type")
        if not isinstance(x, str) or not isinstance(y, str):
            raise TypeError("chart field names must be strings")
        if len(data) > 2_000:
            raise ValueError("chart data cannot exceed 2,000 records")
        frame = pd.DataFrame(data)
        if x not in frame.columns or y not in frame.columns:
            raise ValueError("requested chart field is not present in data")

        figure_factory = {"bar": px.bar, "line": px.line, "scatter": px.scatter}
        figure = figure_factory[chart_type](frame, x=x, y=y)
        return {
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "figure": json.loads(figure.to_json()),
        }

    def predict_repurchase(self, features: dict[str, Any]) -> dict[str, float]:
        """Score exactly the six approved first-order features."""
        missing = set(FEATURE_COLUMNS).difference(features)
        if missing:
            raise ValueError("missing required prediction features")
        feature_frame = pd.DataFrame(
            [{column: features[column] for column in FEATURE_COLUMNS}],
            columns=list(FEATURE_COLUMNS),
        )
        probability = float(self._predictor(feature_frame))
        if not 0.0 <= probability <= 1.0:
            raise ValueError("predictor did not return a probability")
        return {"repurchase_probability": probability}

    def simulate_campaign(
        self,
        probabilities: Sequence[float],
        budget: float,
        contact_cost: float,
        average_repurchase_revenue: float,
        scenarios: Sequence[Scenario | dict[str, Any]],
        max_contact_fraction: float,
    ) -> list[dict[str, float | int | str]]:
        """Run the existing incremental-profit simulator with explicit inputs."""
        if len(probabilities) > 2_000 or len(scenarios) > 2_000:
            raise ValueError("campaign payload cannot exceed 2,000 entries")
        normalized_scenarios = tuple(
            _normalize_scenario(scenario) for scenario in scenarios
        )
        results = self._campaign_simulator(
            pd.Series(probabilities, dtype=float),
            budget,
            contact_cost,
            average_repurchase_revenue,
            normalized_scenarios,
            max_contact_fraction,
        )
        return [asdict(result) for result in results]

    def definitions(self) -> list[ToolDefinition]:
        """Expose exactly the five governed tools to the LangChain client."""
        return [
            ToolDefinition(
                "get_metric_definition",
                "Read one governed business metric definition.",
                _object_schema({"name": {"type": "string"}}, ["name"]),
            ),
            ToolDefinition(
                "run_safe_sql",
                "Run one bounded SELECT against approved marts views.",
                _object_schema({"sql": {"type": "string"}}, ["sql"]),
            ),
            ToolDefinition(
                "create_chart",
                "Create a bar, line, or scatter chart from supplied records.",
                _object_schema(
                    {
                        "chart_type": {"type": "string", "enum": ["bar", "line", "scatter"]},
                        "data": {
                            "type": "array",
                            "items": {"type": "object"},
                            "maxItems": 2_000,
                        },
                        "x": {"type": "string"},
                        "y": {"type": "string"},
                    },
                    ["chart_type", "data", "x", "y"],
                ),
            ),
            ToolDefinition(
                "predict_repurchase",
                "Score the approved first-order repurchase features.",
                _object_schema({"features": {"type": "object"}}, ["features"]),
            ),
            ToolDefinition(
                "simulate_campaign",
                "Simulate incremental marketing profit under explicit scenarios.",
                _object_schema(
                    {
                        "probabilities": {
                            "type": "array",
                            "items": {"type": "number"},
                            "maxItems": 2_000,
                        },
                        "budget": {"type": "number"},
                        "contact_cost": {"type": "number"},
                        "average_repurchase_revenue": {"type": "number"},
                        "scenarios": {
                            "type": "array",
                            "items": {"type": "object"},
                            "maxItems": 2_000,
                        },
                        "max_contact_fraction": {"type": "number"},
                    },
                    [
                        "probabilities",
                        "budget",
                        "contact_cost",
                        "average_repurchase_revenue",
                        "scenarios",
                        "max_contact_fraction",
                    ],
                ),
            ),
        ]


def _object_schema(
    properties: dict[str, dict[str, Any]], required: list[str]
) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required}


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize DataFrame records so an agent result can always become JSON."""
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _normalize_scenario(value: Scenario | dict[str, Any]) -> Scenario:
    """Convert one JSON tool argument into the project's explicit Scenario type."""
    if isinstance(value, Scenario):
        return value
    if not isinstance(value, dict) or set(value) != {"name", "uplift_rate"}:
        raise ValueError("scenario must contain only name and uplift_rate")
    name = value["name"]
    uplift_rate = value["uplift_rate"]
    if not isinstance(name, str) or not name:
        raise ValueError("scenario name must be a non-empty string")
    if (
        isinstance(uplift_rate, bool)
        or not isinstance(uplift_rate, Real)
        or not isfinite(uplift_rate)
    ):
        raise ValueError("scenario uplift_rate must be a finite number")
    return Scenario(name=name, uplift_rate=float(uplift_rate))
