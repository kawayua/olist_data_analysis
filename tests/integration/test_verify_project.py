from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts.verify_project import (
    REQUIRED_ARTIFACTS,
    REQUIRED_MARTS,
    REQUIRED_RAW_FILES,
    REQUIRED_SCHEMAS,
    VerificationDependencies,
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
    assert any("customer_360" in message for message in result.messages)


def test_verification_reports_missing_artifact(healthy_dependencies: FakeDependencies) -> None:
    (healthy_dependencies.root / REQUIRED_ARTIFACTS[0]).unlink()

    result = verify_project(
        healthy_dependencies.dependencies(), require_source_data=False, full=False
    )

    assert result.ok is False
    assert any(REQUIRED_ARTIFACTS[0] in message for message in result.messages)
    assert any("quality workflow" in message.lower() for message in result.messages)


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
