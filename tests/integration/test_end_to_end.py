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


def test_portfolio_documents_cover_local_reproduction_and_evidence() -> None:
    required_content = {
        "README.md": (
            "中文",
            "English",
            "docker compose up -d",
            "streamlit run app/Home.py",
        ),
        "docs/data-dictionary.md": ("raw", "staging", "warehouse", "marts"),
        "docs/metric-dictionary.md": ("GMV", "90", "复购"),
        "docs/architecture.md": ("```mermaid", "只读 SQL"),
        "docs/interview-guide.md": ("3", "10", "追问"),
        "docs/retrospectives/final.md": ("真实模型", "限制"),
    }

    for document, expected_terms in required_content.items():
        content = Path(document).read_text(encoding="utf-8")
        for term in expected_terms:
            assert term in content, f"{document} must document {term!r}"
