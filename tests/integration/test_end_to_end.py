from pathlib import Path

from scripts.verify_project import REQUIRED_ARTIFACTS


def test_delivery_entrypoints_expose_portable_postgres_volume() -> None:
    assert "${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}" in Path(
        "docker-compose.yml"
    ).read_text(encoding="utf-8")
    assert "POSTGRES_VOLUME_NAME=data_analysis_postgres_data" in Path(
        ".env.example"
    ).read_text(encoding="utf-8")


def test_artifact_only_delivery_contract_declares_required_paths() -> None:
    assert Path("scripts/verify_project.py").is_file()
    assert REQUIRED_ARTIFACTS == (
        "artifacts/quality/latest.json",
        "artifacts/models/repurchase_pipeline.joblib",
        "artifacts/models/metrics.json",
        "artifacts/agent/evaluation.json",
    )
