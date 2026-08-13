import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def test_monthly_growth_has_complete_month_flag_and_unique_months():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/030_monthly_growth.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows, months, incomplete_months = connection.execute(
            text(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT month_start),
                    COUNT(*) FILTER (WHERE NOT is_complete_month)
                FROM marts.monthly_growth
                """
            )
        ).one()

    assert rows == months
    assert incomplete_months == 2


def test_monthly_growth_has_growth_driver_metrics():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'marts'
                      AND table_name = 'monthly_growth'
                    """
                )
            ).scalars()
        )

    assert {
        "active_customers_mom_pct",
        "order_count_mom_pct",
        "item_revenue_aov_mom_pct",
        "average_review_score",
    } <= columns
