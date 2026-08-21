from pathlib import Path


def test_delivery_entrypoints_expose_portable_postgres_volume() -> None:
    assert "${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}" in Path(
        "docker-compose.yml"
    ).read_text(encoding="utf-8")
    assert "POSTGRES_VOLUME_NAME=data_analysis_postgres_data" in Path(
        ".env.example"
    ).read_text(encoding="utf-8")
