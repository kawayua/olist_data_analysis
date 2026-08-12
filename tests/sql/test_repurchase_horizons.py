import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def test_repurchase_horizons_has_three_windows_and_matches_customer_360_90d():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/031_repurchase_horizons.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        horizons, eligible_90d, repurchased_90d = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.repurchase_horizons),
                    (
                        SELECT eligible_customers
                        FROM marts.repurchase_horizons
                        WHERE horizon_days = 90
                    ),
                    (
                        SELECT repurchased_customers
                        FROM marts.repurchase_horizons
                        WHERE horizon_days = 90
                    )
                """
            )
        ).one()

    assert horizons == 3
    assert eligible_90d == 75387
    assert repurchased_90d == 1514
