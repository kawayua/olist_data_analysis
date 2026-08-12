import subprocess
import sys
from pathlib import Path


def test_build_marts_script_rebuilds_cohort_retention():
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/031_cohort_retention.sql" in result.stdout
