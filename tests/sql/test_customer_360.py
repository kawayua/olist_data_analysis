import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def test_customer_360_has_one_row_per_delivered_customer_and_valid_labels():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/032_customer_360.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        actual, expected, duplicates, invalid_labels = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.customer_360),
                    (
                        SELECT COUNT(DISTINCT customer_key)
                        FROM warehouse.fact_orders
                        WHERE order_status = 'delivered'
                    ),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT customer_key)
                        FROM marts.customer_360
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.customer_360
                        WHERE (eligible_for_90d AND repurchased_within_90d IS NULL)
                           OR (NOT eligible_for_90d AND repurchased_within_90d IS NOT NULL)
                    )
                """
            )
        ).one()

    assert actual == expected
    assert duplicates == 0
    assert invalid_labels == 0


def test_customer_strategy_table_covers_all_segments_and_customer_360_has_snapshot_time():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/032_customer_segment_strategy.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        strategy_rows, missing_actions, missing_feature_time = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.customer_segment_strategy),
                    (
                        SELECT COUNT(*)
                        FROM marts.customer_segment_strategy
                        WHERE recommended_action = ''
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.customer_360
                        WHERE feature_available_at IS NULL
                    )
                """
            )
        ).one()

    assert strategy_rows == 5
    assert missing_actions == 0
    assert missing_feature_time == 0
