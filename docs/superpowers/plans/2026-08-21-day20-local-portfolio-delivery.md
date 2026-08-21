# Day 20 Local Portfolio Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Chinese-English Olist portfolio that can be checked locally without rebuilding data or calling a live LLM.

**Architecture:** PostgreSQL runs in Docker and Streamlit runs through local Python 3.13. An injected verifier observes readiness only; documentation gives matching bilingual normal and recovery paths.

**Tech Stack:** Python 3.13, Docker Compose/PostgreSQL 16, SQLAlchemy, pytest, Ruff, Streamlit, Mermaid, Markdown.

**Spec:** `docs/superpowers/specs/2026-08-21-day20-local-portfolio-delivery-design.md`

## Global Constraints

- Docker runs PostgreSQL only; Streamlit starts with `py -3.13 -m streamlit run app/Home.py --server.port 8501`.
- Default verification must not download CSVs, mutate data, build marts, train models, or invoke LLMs.
- `--full` runs pytest only against the explicit non-database directories `tests/agent tests/analytics tests/ingestion tests/integration tests/ml tests/validation tests/visualization`, then runs `py -3.13 -m ruff check src tests app scripts`; it never includes `tests/sql` or a build/bootstrap/load entrypoint.
- Raw CSVs are never committed; require all nine only with `--require-source-data`.
- Never print credentials, API keys or connection URLs. `.env` stays ignored.
- `POSTGRES_VOLUME_NAME` defaults to `data_analysis_postgres_data`; a local override can attach an existing volume.
- Chinese and English statements must match. Fake Agent evaluation is not live-model accuracy.

---

### Task 1: Make the Docker volume portable

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Test: `tests/integration/test_end_to_end.py`

**Interfaces:** consumes optional `POSTGRES_VOLUME_NAME`; produces Compose volume name `${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}` and safe `.env.example` default.

- [ ] **Step 1: Write the failing contract**

```python
def test_delivery_entrypoints_expose_portable_postgres_volume() -> None:
    assert "${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}" in Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_VOLUME_NAME=data_analysis_postgres_data" in Path(".env.example").read_text(encoding="utf-8")
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/integration/test_end_to_end.py::test_delivery_entrypoints_expose_portable_postgres_volume -v`

Expected: FAIL because Compose and the example file lack the contract.

- [ ] **Step 3: Implement the minimal configuration**

```yaml
volumes:
  postgres_data:
    name: ${POSTGRES_VOLUME_NAME:-data_analysis_postgres_data}
```

Add `POSTGRES_VOLUME_NAME=data_analysis_postgres_data` to `.env.example`, with a comment that local existing-volume overrides must not be committed.

- [ ] **Step 4: Verify GREEN and commit**

Run: `py -3.13 -m pytest tests/integration/test_end_to_end.py::test_delivery_entrypoints_expose_portable_postgres_volume -v`

Expected: PASS without Docker or `.env`.

Commit: `git add docker-compose.yml .env.example tests/integration/test_end_to_end.py; git commit -m "feat: configure portable local postgres volume"`

### Task 2: Add the non-destructive verifier

**Files:**
- Create: `scripts/verify_project.py`
- Create: `tests/integration/test_verify_project.py`
- Modify: `tests/integration/test_end_to_end.py`

**Interfaces:**
- Produces `VerificationResult(ok: bool, messages: tuple[str, ...])`.
- Produces `verify_project(dependencies, *, require_source_data: bool, full: bool) -> VerificationResult`.
- Produces `main(argv: Sequence[str] | None = None) -> int` with `--full` and `--require-source-data`.
- Required schemas: `raw`, `staging`, `warehouse`, `marts`.
- Required marts: `monthly_growth`, `cohort_retention`, `customer_360`, `product_performance`, `delivery_experience`, `delivery_order_analysis`, `state_performance`, `state_monthly_performance`, `ml_customer_features`.
- Required artifacts: quality JSON, repurchase pipeline, metrics JSON and Agent fake evaluation JSON at the paths in the design spec.

- [ ] **Step 1: Write failing injected-boundary tests**

```python
def test_default_verification_is_non_destructive(tmp_path):
    deps = passing_dependencies(project_root=tmp_path)
    assert verify_project(deps, require_source_data=False, full=False).ok
    assert deps.commands == []

def test_database_failure_has_safe_compose_recovery(tmp_path):
    result = verify_project(passing_dependencies(tmp_path, database_connectable=False), require_source_data=False, full=False)
    assert not result.ok
    assert "docker compose up -d" in "\n".join(result.messages)
    assert "analytics@" not in "\n".join(result.messages)

def test_full_mode_runs_exact_commands_after_health(tmp_path):
    deps = passing_dependencies(project_root=tmp_path)
    assert verify_project(deps, require_source_data=False, full=True).ok
    assert deps.commands[0] == ("py", "-3.13", "-m", "pytest", "-v", "tests/agent", "tests/analytics", "tests/ingestion", "tests/integration", "tests/ml", "tests/validation", "tests/visualization")
    assert "tests/sql" not in deps.commands[0]
```

Add sibling tests for Docker unavailable, missing schema/mart/artifact, tracked `.env`, one absent raw CSV under `--require-source-data`, and a failed full command. Each must assert its exact safe recovery guidance.

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/integration/test_verify_project.py -v`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the dependencies and production adapters**

```python
@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    messages: tuple[str, ...]

def verify_project(dependencies: VerificationDependencies, *, require_source_data: bool, full: bool) -> VerificationResult:
    """Observe readiness without changing data, services, model state, or LLM state."""
```

Production adapters inspect Docker, use a short SQLAlchemy schema/table query, reject empty/corrupt artifacts, and require both `git ls-files --error-unmatch .env` to fail and `git check-ignore --quiet .env` to pass. Store nine CSV names and required marts/artifacts in constants. Do not call bootstrap/loading/build/train/evaluate/Streamlit/LLM. Run the explicit safe full commands only after health passes, and return non-zero from CLI for any failure.

- [ ] **Step 4: Add the no-network delivery contract and verify GREEN**

```python
def test_final_delivery_has_non_networked_verification_contract() -> None:
    assert Path("scripts/verify_project.py").is_file()
    manifest = json.loads(Path("artifacts/manifest.json").read_text(encoding="utf-8"))
    assert manifest["policy"] == "generated-after-clone"
    assert {entry["path"] for entry in manifest["artifacts"]} == set(REQUIRED_ARTIFACTS)
```

Run: `py -3.13 -m pytest tests/integration/test_verify_project.py tests/integration/test_end_to_end.py -v`

Expected: PASS with fakes/temp paths and no Docker, database, network or LLM.

- [ ] **Step 5: Commit**

Commit: `git add scripts/verify_project.py tests/integration/test_verify_project.py tests/integration/test_end_to_end.py; git commit -m "feat: add non-destructive local project verification"`

### Task 3: Write matching Chinese-English portfolio documentation

**Files:**
- Create: `README.md`
- Create: `docs/data-dictionary.md`
- Create: `docs/metric-dictionary.md`
- Create: `docs/architecture.md`
- Create: `docs/interview-guide.md`
- Create: `docs/retrospectives/final.md`
- Modify: `tests/integration/test_end_to_end.py`

**Interfaces:** consumes marts, `src/ml`, `src/agent`, artifacts and `data/README.md`; produces six Markdown entrypoints with matching bilingual evidence and limitations.

- [ ] **Step 1: Write the failing documentation contract**

```python
def test_portfolio_documents_cover_local_reproduction_and_evidence() -> None:
    required = {
        "README.md": ["中文", "English", "docker compose up -d", "streamlit run app/Home.py"],
        "docs/data-dictionary.md": ["raw", "staging", "warehouse", "marts"],
        "docs/metric-dictionary.md": ["GMV", "90", "复购"],
        "docs/architecture.md": ["```mermaid", "只读 SQL"],
        "docs/interview-guide.md": ["3", "10", "追问"],
        "docs/retrospectives/final.md": ["真实模型", "限制"],
    }
    for filename, tokens in required.items():
        assert all(token in Path(filename).read_text(encoding="utf-8") for token in tokens)
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/integration/test_end_to_end.py::test_portfolio_documents_cover_local_reproduction_and_evidence -v`

Expected: FAIL because the entrypoints are absent.

- [ ] **Step 3: Write documentation from governed sources**

README covers paired Chinese-English project value, verified findings, nine-CSV boundary, Docker/Python quick start, portable volume override, strict source-data mode, generated-after-clone artifacts, structure, dashboard, temporal ML, Agent safety/fake evaluation and limits. Documents distinguish purchase-anchored analysis-mart labels (first-purchase `purchased_at`, completeness through data-end `MAX(purchased_at)`) from the delivery-anchored ML label (first-delivery prediction time and later delivered-order `purchased_at`). Data dictionary records grain/key/source/fields for raw, staging, warehouse and marts. Metric dictionary defines GMV, item revenue, order/customer counts, delay rate, rating and both 90-day repurchase contexts. Architecture contains a Mermaid CSV-to-marts-to-Dashboard/ML/Agent diagram and explains monetary preaggregation, observation windows and AST-guarded read-only/audited SQL. Interview guide provides paired 3-/10-minute narration plus ten candid technical Q&As. Retrospective records findings, double-counting risk, leakage control, model/business caveats, Agent safety, observed provider instability and next improvements.

- [ ] **Step 4: Verify GREEN and rendered content**

Run: `py -3.13 -m pytest tests/integration/test_end_to_end.py::test_portfolio_documents_cover_local_reproduction_and_evidence -v`

Expected: PASS. Render/inspect every document: no credentials, local legacy volume name, or fake-evaluation-as-live-accuracy claim.

- [ ] **Step 5: Commit**

Commit: `git add README.md docs/data-dictionary.md docs/metric-dictionary.md docs/architecture.md docs/interview-guide.md docs/retrospectives/final.md tests/integration/test_end_to_end.py; git commit -m "docs: add bilingual local portfolio delivery"`

### Task 4: Perform and record acceptance

**Files:**
- Modify: `docs/retrospectives/final.md`
- Modify: `docs/learning/week-2.md`
- Modify: `tests/integration/test_end_to_end.py`

**Interfaces:** produces a dated Day 20 learning record and a final evidence section based only on actual command outcomes.

- [ ] **Step 1: Write the failing acceptance-record assertion**

```python
def test_final_retrospective_records_non_live_reproducibility_boundary() -> None:
    content = Path("docs/retrospectives/final.md").read_text(encoding="utf-8")
    assert "verify_project.py --full" in content
    assert "不调用真实" in content
```

- [ ] **Step 2: Verify RED**

Run: `py -3.13 -m pytest tests/integration/test_end_to_end.py::test_final_retrospective_records_non_live_reproducibility_boundary -v`

Expected: FAIL before acceptance is recorded.

- [ ] **Step 3: Run acceptance and record only observed results**

```powershell
py -3.13 scripts/verify_project.py
py -3.13 scripts/verify_project.py --full
py -3.13 -m ruff check src tests app scripts
```

If Docker or CSVs are unavailable, document the actual limitation and recovery rather than claim success.

- [ ] **Step 4: Verify final contracts**

Run: `py -3.13 -m pytest tests/integration/test_verify_project.py tests/integration/test_end_to_end.py -v`

Expected: PASS, including the non-live boundary.

- [ ] **Step 5: Commit**

Commit: `git add docs/retrospectives/final.md docs/learning/week-2.md tests/integration/test_end_to_end.py; git commit -m "docs: record Day 20 reproducibility verification"`

## Final Verification Checklist

- [ ] Default verification does not mutate data/model/LLM state.
- [ ] Full verification makes no live LLM request.
- [ ] Explicit non-database pytest directories and Ruff pass; `tests/sql` remains developer-only and isolated from readiness verification.
- [ ] `.env` is ignored and untracked.
- [ ] Rendered README covers startup, volume override, raw data recovery and live-model limits.
