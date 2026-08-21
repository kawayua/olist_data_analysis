from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

import scripts.verify_project as verifier
from scripts.verify_project import (
    REQUIRED_ARTIFACTS,
    REQUIRED_MARTS,
    REQUIRED_RAW_FILES,
    REQUIRED_SCHEMAS,
    VerificationDependencies,
    main,
    verify_project,
)


class FakeDependencies:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.docker_ok = True
        self.database_ok = True
        self.schemas = set(REQUIRED_SCHEMAS)
        self.marts = set(REQUIRED_MARTS)
        self.env_tracked = False
        self.commands: list[tuple[str, ...]] = []
        self.command_results: list[bool] = []

    def docker_available(self) -> bool:
        return self.docker_ok

    def database_ready(self) -> bool:
        return self.database_ok

    def available_schemas(self) -> set[str]:
        return self.schemas

    def available_marts(self) -> set[str]:
        return self.marts

    def is_env_tracked(self) -> bool:
        return self.env_tracked

    def run_command(self, command: Sequence[str]) -> bool:
        self.commands.append(tuple(command))
        return self.command_results.pop(0) if self.command_results else True

    def dependencies(self) -> VerificationDependencies:
        return VerificationDependencies(
            root=self.root,
            docker_available=self.docker_available,
            database_ready=self.database_ready,
            available_schemas=self.available_schemas,
            available_marts=self.available_marts,
            is_env_tracked=self.is_env_tracked,
            run_command=self.run_command,
        )


@pytest.fixture
def healthy_dependencies(tmp_path: Path) -> FakeDependencies:
    dependencies = FakeDependencies(tmp_path)
    for relative_path in REQUIRED_ARTIFACTS:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ready", encoding="utf-8")
    return dependencies


def test_healthy_default_verification_avoids_full_commands(
    healthy_dependencies: FakeDependencies,
) -> None:
    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is True
    assert result.messages == ("Project readiness checks passed.",)
    assert healthy_dependencies.commands == []


def test_default_full_commands_have_a_longer_timeout_than_observations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[tuple[str, ...], int]] = []

    def run_quietly(command: Sequence[str], *, cwd: Path, timeout: int) -> bool:
        assert cwd == tmp_path
        calls.append((tuple(command), timeout))
        return True

    monkeypatch.setattr(verifier, "_run_quietly", run_quietly)
    dependencies = verifier.default_dependencies(tmp_path)

    dependencies.docker_available()
    dependencies.is_env_tracked()
    dependencies.run_command(verifier.FULL_COMMANDS[0])

    assert calls == [
        (("docker", "info"), 15),
        (("git", "ls-files", "--error-unmatch", ".env"), 15),
        (("py", "-3.13", "-m", "pytest", "-v"), 600),
    ]


def test_cli_returns_zero_for_healthy_dependencies(
    healthy_dependencies: FakeDependencies, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main([], dependencies=healthy_dependencies.dependencies())

    assert exit_code == 0
    assert capsys.readouterr().out == "Project readiness checks passed.\n"


def test_cli_returns_one_for_failed_dependencies(
    healthy_dependencies: FakeDependencies, capsys: pytest.CaptureFixture[str]
) -> None:
    healthy_dependencies.docker_ok = False

    exit_code = main([], dependencies=healthy_dependencies.dependencies())

    assert exit_code == 1
    assert capsys.readouterr().out == (
        "Docker is unavailable. Start Docker Desktop, then run docker compose up -d.\n"
    )


def test_direct_script_entrypoint_imports_project_modules_without_services() -> None:
    completed = subprocess.run(
        (sys.executable, "scripts/verify_project.py"),
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    combined_output = completed.stdout + completed.stderr
    assert completed.returncode in (0, 1)
    assert "ModuleNotFoundError" not in combined_output
    assert "Traceback" not in combined_output


def test_verification_reports_docker_failure(healthy_dependencies: FakeDependencies) -> None:
    healthy_dependencies.docker_ok = False

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert any("Docker Desktop" in message for message in result.messages)


def test_verification_reports_database_failure(healthy_dependencies: FakeDependencies) -> None:
    healthy_dependencies.database_ok = False

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert any("docker compose up -d" in message for message in result.messages)


def test_verification_reports_missing_schema(healthy_dependencies: FakeDependencies) -> None:
    healthy_dependencies.schemas.remove("warehouse")

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert any("warehouse" in message for message in result.messages)
    assert any("build_marts.py" in message for message in result.messages)


def test_verification_reports_missing_mart(healthy_dependencies: FakeDependencies) -> None:
    healthy_dependencies.marts.remove("customer_360")

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert result.messages == (
        "Missing marts: customer_360. Run py -3.13 scripts/build_marts.py.",
    )


def test_verification_reports_missing_artifact(healthy_dependencies: FakeDependencies) -> None:
    (healthy_dependencies.root / REQUIRED_ARTIFACTS[0]).unlink()

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert result.messages == (
        (
            "Missing or unreadable artifacts/quality/latest.json. "
            "Run py -3.13 scripts/run_quality_checks.py to recreate the quality artifact."
        ),
    )


@pytest.mark.parametrize(
    ("relative_path", "expected_message"),
    [
        (
            "artifacts/models/repurchase_pipeline.joblib",
            (
                "Missing or unreadable artifacts/models/repurchase_pipeline.joblib. "
                "Run py -3.13 scripts/train_model.py to recreate model artifacts."
            ),
        ),
        (
            "artifacts/agent/evaluation.json",
            (
                "Missing or unreadable artifacts/agent/evaluation.json. "
                "Run py -3.13 scripts/evaluate_agent.py --mode fake to recreate it."
            ),
        ),
    ],
)
def test_verification_provides_exact_artifact_recovery_guidance(
    healthy_dependencies: FakeDependencies,
    relative_path: str,
    expected_message: str,
) -> None:
    (healthy_dependencies.root / relative_path).unlink()

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.messages == (expected_message,)


def test_verification_reports_tracked_environment_file(
    healthy_dependencies: FakeDependencies,
) -> None:
    healthy_dependencies.env_tracked = True

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert any(".env" in message for message in result.messages)
    assert all("password" not in message.lower() for message in result.messages)


def test_strict_verification_reports_missing_raw_file(
    healthy_dependencies: FakeDependencies,
) -> None:
    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=True, full=False
    )

    assert result.ok is False
    assert any(REQUIRED_RAW_FILES[0] in message for message in result.messages)
    assert any("data/README.md" in message for message in result.messages)
    assert result.messages == (
        (
            "Missing required source data: olist_customers_dataset.csv, "
            "olist_orders_dataset.csv, olist_order_items_dataset.csv, "
            "olist_order_payments_dataset.csv, olist_order_reviews_dataset.csv, "
            "olist_products_dataset.csv, olist_sellers_dataset.csv, "
            "olist_geolocation_dataset.csv, product_category_name_translation.csv. "
            "See data/README.md."
        ),
    )


def test_full_verification_reports_failed_command(
    healthy_dependencies: FakeDependencies,
) -> None:
    healthy_dependencies.command_results = [False]

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=True
    )

    assert result.ok is False
    assert any("pytest" in message for message in result.messages)
    assert healthy_dependencies.commands == [("py", "-3.13", "-m", "pytest", "-v")]


def test_full_verification_runs_the_exact_command_list(
    healthy_dependencies: FakeDependencies,
) -> None:
    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=True
    )

    assert result.ok is True
    assert healthy_dependencies.commands == [
        ("py", "-3.13", "-m", "pytest", "-v"),
        ("py", "-3.13", "-m", "ruff", "check", "src", "tests", "app", "scripts"),
    ]
