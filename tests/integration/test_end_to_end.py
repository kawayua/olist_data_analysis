import json
from pathlib import Path

from scripts.verify_project import REQUIRED_ARTIFACTS


def test_delivery_entrypoints_expose_portable_postgres_volume() -> None:
    assert "${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}" in Path(
        "docker-compose.yml"
    ).read_text(encoding="utf-8")
    assert "POSTGRES_VOLUME_NAME=data_analysis_postgres_data" in Path(
        ".env.example"
    ).read_text(encoding="utf-8")


def test_generated_after_clone_artifact_manifest_declares_reproducible_policy() -> None:
    assert Path("scripts/verify_project.py").is_file()
    manifest = json.loads(Path("artifacts/manifest.json").read_text(encoding="utf-8"))
    assert manifest["policy"] == "generated-after-clone"
    entries = {entry["path"]: entry for entry in manifest["artifacts"]}
    assert tuple(entries) == REQUIRED_ARTIFACTS
    assert entries == {
        "artifacts/quality/latest.json": {
            "path": "artifacts/quality/latest.json",
            "generation_command": "py -3.13 scripts/run_quality_checks.py",
            "prerequisite": "Populated PostgreSQL warehouse and marts",
        },
        "artifacts/models/repurchase_pipeline.joblib": {
            "path": "artifacts/models/repurchase_pipeline.joblib",
            "generation_command": "py -3.13 scripts/train_model.py",
            "prerequisite": "Populated marts.ml_customer_features",
        },
        "artifacts/models/metrics.json": {
            "path": "artifacts/models/metrics.json",
            "generation_command": "py -3.13 scripts/train_model.py",
            "prerequisite": "Populated marts.ml_customer_features",
        },
        "artifacts/agent/evaluation.json": {
            "path": "artifacts/agent/evaluation.json",
            "generation_command": "py -3.13 scripts/evaluate_agent.py --mode fake",
            "prerequisite": "Installed Python dependencies and configs/agent_questions.yml",
        },
    }


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

    readme = Path("README.md").read_text(encoding="utf-8")
    assert "py -3.13 scripts/load_raw.py --data-dir data/raw" in readme

    readme = Path("README.md").read_text(encoding="utf-8")
    assert "POSTGRES_VOLUME_NAME=data_analysis_postgres_data" in readme
    assert "py -3.13 scripts/verify_project.py --require-source-data" in readme
    assert "generated-after-clone" in readme

    metric_dictionary = Path("docs/metric-dictionary.md").read_text(encoding="utf-8")
    assert "分析集市 / analysis marts" in metric_dictionary
    assert "首购 `purchased_at` / first-purchase `purchased_at`" in metric_dictionary
    assert "数据终点 `MAX(purchased_at)` / data-end `MAX(purchased_at)`" in metric_dictionary
    assert "ML 标签 / ML label" in metric_dictionary
    assert "首笔已送达订单的送达时间 / delivery time of the first delivered order" in metric_dictionary

    for document in (
        "README.md",
        "docs/architecture.md",
        "docs/retrospectives/final.md",
    ):
        content = Path(document).read_text(encoding="utf-8")
        assert "py -3.13 scripts/run_quality_checks.py" in content
        assert "读取现有数据库" in content
        assert "reads the existing database" in content
        assert "artifacts/quality/latest.json" in content


def test_data_dictionary_matches_mart_grain_key_and_source_contracts() -> None:
    content = Path("docs/data-dictionary.md").read_text(encoding="utf-8")

    assert (
        "`customer_segment_strategy` | 每客户分群一行；`customer_segment` | "
        "`customer_360` 的分群汇总 + 五条策略规则"
    ) in content
    assert (
        "`repurchase_horizons` | 每个天数窗口一行；`horizon_days` | delivered orders"
    ) in content
    assert (
        "`repurchase_behavior` | 首购品类 × 天数窗口；"
        "(`first_purchase_category`, `horizon_days`)"
    ) in content
    assert (
        "`monthly_growth` | 每自然月；`month_start` | delivered "
        "`warehouse.fact_orders` + `warehouse.fact_reviews`"
    ) in content
    assert (
        "`delivery_rating_analysis` | 每配送延迟桶一行；`delivery_delay_bucket` | "
        "`warehouse.fact_orders` + `warehouse.fact_reviews` | "
        "订单数、相对预计送达天数均值、评分均值"
    ) in content
    assert (
        "`state_monthly_performance` | 每自然月 × 客户州；"
        "(`month_start`, `customer_state`) | delivered "
        "`warehouse.fact_orders` + `raw.customers` | "
        "订单/客户、商品/支付金额、两种 AOV、完整月标记"
    ) in content
    assert (
        "`state_performance` | 每客户州；`customer_state` | delivered "
        "`warehouse.fact_orders` + `raw.customers` + `warehouse.fact_reviews` + "
        "`marts.customer_360` | 订单/客户、商品/支付金额、商品金额 AOV、"
        "延迟、配送、评分、90 天复购"
    ) in content
    assert (
        "`customer_value_analysis` | 每客户分群一行；`customer_segment` | "
        "`marts.customer_360` | 客户数、商品金额与占比、RFM 均值、"
        "首购/二购/多购客户及金额"
    ) in content


def test_day20_final_retrospective_records_acceptance_results() -> None:
    content = Path("docs/retrospectives/final.md").read_text(encoding="utf-8")

    assert "## Day 20 验收记录 / Day 20 acceptance record" in content
    assert "verify_project.py --full" in content
    assert "不调用真实" in content


def test_day20_retrospective_states_non_destructive_acceptance_boundary() -> None:
    content = Path("docs/retrospectives/final.md").read_text(encoding="utf-8")

    assert "tests/sql" in content
    assert "经审计的精确测试文件" in content
    assert "audited exact test files" in content


def test_day20_retrospective_invalidates_the_old_broad_pytest_evidence() -> None:
    content = Path("docs/retrospectives/final.md").read_text(encoding="utf-8")

    assert "旧结果不能证明非破坏性交付" in content
    assert "historical results do not prove non-destructive delivery" in content
