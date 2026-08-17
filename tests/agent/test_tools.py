from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.agent.tools import AnalysisTools, SQLAlchemyReadOnlyExecutor
from src.ml.roi import Scenario, SimulationResult


class FakeExecutor:
    def __init__(self):
        self.sql: str | None = None

    def read_only_query(self, sql: str) -> pd.DataFrame:
        self.sql = sql
        return pd.DataFrame(
            [{"month_start": "2017-01-01", "item_revenue": 100.0}]
        )


def test_safe_sql_uses_validated_query_and_returns_bounded_records():
    executor = FakeExecutor()
    tools = AnalysisTools(
        executor=executor, allowed_views={"marts.monthly_growth"}
    )

    result = tools.run_safe_sql(
        "select month_start, item_revenue from marts.monthly_growth"
    )

    assert "LIMIT 500" in executor.sql.upper()
    assert result["rows"] == [{"month_start": "2017-01-01", "item_revenue": 100.0}]


def test_safe_sql_serializes_dates_decimals_and_missing_values_for_json():
    class TypedFakeExecutor:
        def read_only_query(self, _sql: str) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "timestamp": pd.Timestamp("2018-01-02 03:04:05"),
                        "date": date(2018, 1, 3),
                        "datetime": datetime(2018, 1, 4, 5, 6, 7, tzinfo=UTC),
                        "amount": Decimal("12.50"),
                        "missing": float("nan"),
                        "missing_time": pd.NaT,
                    }
                ]
            )

    result = AnalysisTools(
        executor=TypedFakeExecutor(), allowed_views={"marts.monthly_growth"}
    ).run_safe_sql("select * from marts.monthly_growth")

    assert result["rows"] == [
        {
            "timestamp": "2018-01-02T03:04:05.000",
            "date": "2018-01-03T00:00:00.000",
            "datetime": "2018-01-04T05:06:07.000Z",
            "amount": 12.5,
            "missing": None,
            "missing_time": None,
        }
    ]


def test_unsafe_sql_never_reaches_the_executor():
    executor = FakeExecutor()
    tools = AnalysisTools(
        executor=executor, allowed_views={"marts.monthly_growth"}
    )

    with pytest.raises(ValueError):
        tools.run_safe_sql("delete from marts.monthly_growth")

    assert executor.sql is None


def test_registered_tools_are_exactly_the_governed_five():
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )

    assert {tool.name for tool in tools.definitions()} == {
        "get_metric_definition",
        "run_safe_sql",
        "create_chart",
        "predict_repurchase",
        "simulate_campaign",
    }


def test_metric_definition_returns_governed_formula():
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )

    result = tools.get_metric_definition("item_revenue")

    assert result["name"] == "item_revenue"
    assert result["formula"]


def test_chart_rejects_unknown_type_and_missing_fields():
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )
    data = [{"month": "2017-01", "revenue": 100.0}]

    with pytest.raises(ValueError, match="chart type"):
        tools.create_chart("pie", data, "month", "revenue")
    with pytest.raises(ValueError, match="field"):
        tools.create_chart("bar", data, "month", "orders")


def test_prediction_receives_only_governed_feature_columns():
    observed: list[str] = []

    def fake_scorer(frame: pd.DataFrame) -> float:
        observed.extend(frame.columns)
        return 0.24

    tools = AnalysisTools(
        executor=FakeExecutor(),
        allowed_views={"marts.monthly_growth"},
        predictor=fake_scorer,
    )
    result = tools.predict_repurchase(
        {
            "first_order_item_count": 1,
            "first_order_item_revenue": 50.0,
            "first_order_freight_revenue": 6.0,
            "first_order_payment_value": 56.0,
            "first_order_delivery_days": 5.0,
            "first_order_distinct_category_count": 1,
            "repurchased_within_90d": True,
        }
    )

    assert result == {"repurchase_probability": 0.24}
    assert observed == [
        "first_order_item_count",
        "first_order_item_revenue",
        "first_order_freight_revenue",
        "first_order_payment_value",
        "first_order_delivery_days",
        "first_order_distinct_category_count",
    ]


def test_campaign_simulation_serializes_incremental_profit():
    def fake_simulator(*_args: object, **_kwargs: object) -> list[SimulationResult]:
        return [
            SimulationResult(
                scenario="baseline",
                contacted_customers=2,
                incremental_repurchases=0.5,
                incremental_revenue=75.0,
                marketing_cost=20.0,
                net_incremental_profit=55.0,
                roi=2.75,
            )
        ]

    tools = AnalysisTools(
        executor=FakeExecutor(),
        allowed_views={"marts.monthly_growth"},
        campaign_simulator=fake_simulator,
    )
    result = tools.simulate_campaign(
        probabilities=[0.4, 0.2],
        budget=20.0,
        contact_cost=10.0,
        average_repurchase_revenue=150.0,
        scenarios=[Scenario("baseline", 0.1)],
        max_contact_fraction=1.0,
    )

    assert result[0]["net_incremental_profit"] == 55.0


def test_campaign_simulation_accepts_json_scenario_payloads():
    observed: list[Scenario] = []

    def fake_simulator(*args: object, **_kwargs: object) -> list[SimulationResult]:
        observed.extend(args[4])
        return []

    tools = AnalysisTools(
        executor=FakeExecutor(),
        allowed_views={"marts.monthly_growth"},
        campaign_simulator=fake_simulator,
    )

    assert tools.simulate_campaign(
        probabilities=[0.4],
        budget=10.0,
        contact_cost=10.0,
        average_repurchase_revenue=150.0,
        scenarios=[{"name": "baseline", "uplift_rate": 0.1}],
        max_contact_fraction=1.0,
    ) == []
    assert observed == [Scenario("baseline", 0.1)]


@pytest.mark.parametrize(
    "scenarios",
    [
        [{"name": "baseline"}],
        [{"name": "baseline", "uplift_rate": 0.1, "extra": "no"}],
        ["baseline"],
    ],
)
def test_campaign_simulation_rejects_malformed_json_scenarios(scenarios):
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )

    with pytest.raises((TypeError, ValueError), match="scenario"):
        tools.simulate_campaign(
            probabilities=[0.4],
            budget=10.0,
            contact_cost=10.0,
            average_repurchase_revenue=150.0,
            scenarios=scenarios,
            max_contact_fraction=1.0,
        )


def test_chart_rejects_more_than_two_thousand_records():
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )
    data = [{"month": str(index), "revenue": float(index)} for index in range(2_001)]

    with pytest.raises(ValueError, match="2,000"):
        tools.create_chart("bar", data, "month", "revenue")


def test_campaign_simulation_rejects_more_than_two_thousand_payload_entries():
    tools = AnalysisTools(
        executor=FakeExecutor(), allowed_views={"marts.monthly_growth"}
    )
    scenarios = [{"name": str(index), "uplift_rate": 0.1} for index in range(2_001)]

    with pytest.raises(ValueError, match="2,000"):
        tools.simulate_campaign(
            probabilities=[0.1] * 2_001,
            budget=10.0,
            contact_cost=10.0,
            average_repurchase_revenue=150.0,
            scenarios=scenarios,
            max_contact_fraction=1.0,
        )


def test_sqlalchemy_executor_sets_read_only_timeout_and_row_cap(monkeypatch):
    commands: list[str] = []

    class FakeConnection:
        def execute(self, command):
            commands.append(str(command))

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(
        "src.agent.tools.pd.read_sql_query",
        lambda _sql, _connection: pd.DataFrame({"value": range(2_001)}),
    )

    result = SQLAlchemyReadOnlyExecutor(FakeEngine()).read_only_query("SELECT 1")

    assert commands == [
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout = '5000ms'",
    ]
    assert len(result) == 2_000
