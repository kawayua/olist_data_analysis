# E-Commerce Growth, Retention & Repurchase Analytics Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在四周内构建一个以数据分析为核心、包含复购预测和可审计问数 Agent 的可部署作品集项目。

**Architecture:** Python 负责导入、验证、分析服务、机器学习和 Agent 编排；PostgreSQL 按 raw、staging、warehouse、marts 分层保存数据；Streamlit 与 Plotly 复用统一指标服务展示结果。所有机器学习特征按时间可用性生成，Agent 只能调用白名单只读工具。

**Tech Stack:** Python 3.11–3.13、Pandas、SQLAlchemy、psycopg、PostgreSQL 16、Streamlit、Plotly、scikit-learn、LightGBM、Pydantic、sqlglot、pytest、Docker Compose、OpenAI-compatible API

## Global Constraints

- 项目工作量保持 70% 数据分析、20% 机器学习、10% Agent。
- 主数据是 Olist 九张 CSV；原始大文件不提交 Git。
- 客户身份统一使用 `customer_unique_id`，订单身份使用 `order_id`。
- 跨粒度连接前必须先聚合，禁止直接连接订单商品与支付后汇总金额。
- 默认有效订单状态为 `delivered`，其他状态单独展示。
- 90 天复购标签只使用拥有完整观察期的样本。
- 训练、验证和测试必须按时间切分，禁止随机切分。
- Agent 只能执行单条 `SELECT`，只能访问白名单 marts 视图，并使用只读数据库账号。
- 所有密钥只从环境变量读取，`.env` 不得提交。
- 每项任务先写失败测试，再写最小实现，通过测试后提交。
- Windows 开发环境当前有 Python 3.13.5，但没有 Docker 和 `psql`；第一个任务先解决可复现环境。

---

## 文件职责图

| 路径 | 职责 |
|---|---|
| `pyproject.toml` | Python 版本、依赖、pytest 与 Ruff 配置 |
| `.env.example` | 无敏感值的环境变量模板 |
| `docker-compose.yml` | PostgreSQL 服务和持久卷 |
| `src/config.py` | 类型化配置入口 |
| `src/database.py` | SQLAlchemy Engine 与事务接口 |
| `src/ingestion/contracts.py` | 九张源表的数据契约 |
| `src/ingestion/loader.py` | CSV 检查、批次导入和导入报告 |
| `src/validation/checks.py` | 主键、外键、范围和时间质量检查 |
| `sql/staging/*.sql` | 类型统一、去重与异常标志 |
| `sql/warehouse/*.sql` | 事实表和维度表 |
| `sql/marts/*.sql` | 分析与机器学习集市 |
| `src/analytics/metrics.py` | 指标注册、定义与查询接口 |
| `src/analytics/statistics.py` | 统计检验及效应量 |
| `src/ml/dataset.py` | 时间安全的样本与标签 |
| `src/ml/train.py` | 模型比较、校准和产物保存 |
| `src/ml/evaluate.py` | PR-AUC、Top-K 和 Lift |
| `src/ml/simulator.py` | 营销情景模拟 |
| `src/agent/client.py` | OpenAI-compatible 模型适配器 |
| `src/agent/tools.py` | 指标、SQL、图表、预测和模拟工具 |
| `src/agent/safety.py` | SQL AST 校验与资源限制 |
| `src/agent/orchestrator.py` | 单 Agent 工具调用循环 |
| `app/Home.py` | Streamlit 首页 |
| `app/pages/*.py` | 业务分析、预测与 Agent 页面 |
| `tests/` | 单元、数据、集成和回归测试 |

## 四周时间表

按每周 5 天、每天约 2–3 小时安排。若某天时间不足，优先完成测试和验收，不牺牲正确性换页面数量。

| 周期 | 日期任务 | 学习重点 | 阶段成果 |
|---|---|---|---|
| 第1周 | Day 1–5，任务1–4 | Python 工程、数据契约、PostgreSQL、ETL、数据质量 | 原始数据可重复入库并输出质量报告 |
| 第2周 | Day 6–10，任务5–8 | 星型模型、SQL 指标、Cohort、RFM | 仓库模型、增长/留存/客户分析集市 |
| 第3周 | Day 11–15，任务9–12 | 统计分析、Streamlit、时间型建模、类别不平衡 | 核心业务结论、交互 Dashboard 与模型基线 |
| 第4周 | Day 16–20，任务13–17 | 模型解释、决策模拟、安全 SQL、Agent 评测、部署表达 | 最终模型、完整应用、测试报告、README 与面试材料 |

---

### Task 1（Day 1–2）: 建立可复现的 Python 与 PostgreSQL 开发环境

**学习目标：** 理解虚拟环境、依赖隔离、环境变量、容器和健康检查。

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`，后续数据库、Agent 和应用统一使用。

- [ ] **Step 1: 安装并验证 Docker Desktop**

从 Docker 官方页面安装 Docker Desktop，启动后运行：

```powershell
docker --version
docker compose version
```

Expected: 两条命令均输出版本号。若公司或学校设备禁止 Docker，则安装 PostgreSQL 16 本地服务，并把后续 `DATABASE_URL` 指向本地实例。

- [ ] **Step 2: 创建失败的配置测试**

```python
from src.config import Settings


def test_database_url_is_built_from_components():
    settings = Settings(
        postgres_user='analytics',
        postgres_password='secret',
        postgres_host='db',
        postgres_port=5432,
        postgres_db='olist',
        llm_api_key='',
        llm_base_url='https://example.invalid/v1',
        llm_model='demo',
    )
    assert settings.database_url == (
        'postgresql+psycopg://analytics:secret@db:5432/olist'
    )
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `python -m pytest tests/test_config.py -v`  
Expected: FAIL，因为 `src.config` 尚不存在或 `Settings` 未定义。

- [ ] **Step 4: 创建项目配置和依赖**

在 `pyproject.toml` 声明：

```toml
[project]
name = 'olist-analytics-platform'
version = '0.1.0'
requires-python = '>=3.11,<3.14'
dependencies = [
  'pandas>=2.2',
  'sqlalchemy>=2.0',
  'psycopg[binary]>=3.2',
  'pydantic>=2.9',
  'pydantic-settings>=2.5',
  'streamlit>=1.40',
  'plotly>=5.24',
  'scikit-learn>=1.5',
  'lightgbm>=4.5',
  'joblib>=1.4',
  'openai>=1.50',
  'sqlglot>=25',
  'pyyaml>=6.0',
]

[project.optional-dependencies]
dev = ['pytest>=8.0', 'pytest-cov>=5.0', 'ruff>=0.6']

[tool.pytest.ini_options]
pythonpath = ['.']
testpaths = ['tests']

[tool.ruff]
line-length = 88
```

创建虚拟环境并安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e '.[dev]'
```

- [ ] **Step 5: 实现类型化配置**

```python
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    postgres_user: str = 'analytics'
    postgres_password: str = 'analytics'
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_db: str = 'olist'
    llm_api_key: str = ''
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_model: str = ''

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f'postgresql+psycopg://{self.postgres_user}:'
            f'{self.postgres_password}@{self.postgres_host}:'
            f'{self.postgres_port}/{self.postgres_db}'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: 创建 PostgreSQL 服务**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: analytics
      POSTGRES_PASSWORD: analytics
      POSTGRES_DB: olist
    ports:
      - '5432:5432'
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U analytics -d olist']
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

`.env.example` 只写变量名和开发默认值；`.gitignore` 至少忽略 `.venv/`、`.env`、`data/raw/*.csv`、`artifacts/`、`__pycache__/` 和 `.pytest_cache/`。

- [ ] **Step 7: 验证环境**

Run:

```powershell
docker compose up -d db
.\.venv\Scripts\python -m pytest tests/test_config.py -v
.\.venv\Scripts\python -m ruff check src tests
```

Expected: PostgreSQL healthy；测试 PASS；Ruff 无错误。

- [ ] **Step 8: 记录学习笔记并提交**

在 `docs/learning/week-1.md` 解释虚拟环境、容器和环境变量各自解决的问题，然后提交：

```powershell
git add pyproject.toml .gitignore .env.example docker-compose.yml src tests docs/learning/week-1.md
git commit -m 'chore: establish reproducible development environment'
```

**验收产出：** 新电脑依据仓库文件可以建立 Python 环境并启动 PostgreSQL。

---

### Task 2（Day 3）: 建立数据清单、数据契约与可重复获取说明

**学习目标：** 理解数据契约、数据血缘和为什么不能把外部数据文件无说明地丢进项目。

**Files:**
- Create: `data/README.md`
- Create: `configs/datasets.yml`
- Create: `src/ingestion/__init__.py`
- Create: `src/ingestion/contracts.py`
- Create: `tests/ingestion/test_contracts.py`

**Interfaces:**
- Produces: `DatasetContract`、`get_contract(name: str) -> DatasetContract`、`required_filenames() -> set[str]`。

- [ ] **Step 1: 写失败测试**

```python
from src.ingestion.contracts import get_contract, required_filenames


def test_orders_contract_declares_primary_key_and_required_columns():
    contract = get_contract('orders')
    assert contract.primary_key == ('order_id',)
    assert {'order_id', 'customer_id', 'order_status'} <= set(contract.columns)


def test_all_nine_source_files_are_declared():
    assert len(required_filenames()) == 9
```

- [ ] **Step 2: 确认测试失败**

Run: `python -m pytest tests/ingestion/test_contracts.py -v`  
Expected: FAIL，因为数据契约尚未实现。

- [ ] **Step 3: 实现数据契约**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetContract:
    name: str
    filename: str
    primary_key: tuple[str, ...]
    columns: tuple[str, ...]


CONTRACTS: dict[str, DatasetContract] = {
    'orders': DatasetContract(
        name='orders',
        filename='olist_orders_dataset.csv',
        primary_key=('order_id',),
        columns=(
            'order_id',
            'customer_id',
            'order_status',
            'order_purchase_timestamp',
            'order_approved_at',
            'order_delivered_carrier_date',
            'order_delivered_customer_date',
            'order_estimated_delivery_date',
        ),
    ),
}


def get_contract(name: str) -> DatasetContract:
    return CONTRACTS[name]


def required_filenames() -> set[str]:
    return {contract.filename for contract in CONTRACTS.values()}
```

在 `CONTRACTS` 中补齐以下九项及主键：`customers(customer_id)`、`orders(order_id)`、`order_items(order_id, order_item_id)`、`payments(order_id, payment_sequential)`、`reviews(review_id, order_id)`、`products(product_id)`、`sellers(seller_id)`、`geolocation()` 和 `category_translation(product_category_name)`。`geolocation` 原始数据允许同一邮编前缀多行，因此不声明源主键；每项的 `columns` 必须逐列抄录 CSV 表头，测试读取一行真实 CSV 并断言集合完全相等。

- [ ] **Step 4: 写数据获取说明**

`data/README.md` 必须列出原始 Kaggle URL、GitHub 说明镜像、九个文件名、放置目录 `data/raw/`、不提交原始数据的原因和许可核对要求。`configs/datasets.yml` 保存逻辑表名、文件名和来源 URL。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/ingestion/test_contracts.py -v`  
Expected: 2 tests PASS。

```powershell
git add data/README.md configs/datasets.yml src/ingestion tests/ingestion
git commit -m 'feat: define Olist source data contracts'
```

**验收产出：** 将九张 CSV 放入 `data/raw/` 后，代码能判断文件是否齐全且字段结构是否符合约定。

---

### Task 3（Day 4）: 建立数据库连接、Schema 和导入批次

**学习目标：** 理解事务、Schema、连接生命周期和导入可追溯性。

**Files:**
- Create: `src/database.py`
- Create: `sql/bootstrap/001_schemas.sql`
- Create: `sql/bootstrap/002_ingestion_runs.sql`
- Create: `scripts/bootstrap_db.py`
- Create: `tests/test_database.py`

**Interfaces:**
- Produces: `get_engine(settings: Settings) -> Engine`、`run_sql_file(engine, path: Path) -> None`。

- [ ] **Step 1: 写数据库 URL 与 SQL 文件执行测试**

```python
from sqlalchemy import create_engine, text

from src.database import run_sql


def test_run_sql_executes_inside_transaction():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    run_sql(engine, 'create table example (id integer primary key)')
    with engine.connect() as conn:
        assert conn.execute(text('select count(*) from example')).scalar_one() == 0
```

- [ ] **Step 2: 确认失败后实现最小接口**

```python
from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config import Settings


def get_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def run_sql(engine: Engine, statement: str) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(statement)


def run_sql_file(engine: Engine, path: Path) -> None:
    run_sql(engine, path.read_text(encoding='utf-8'))
```

- [ ] **Step 3: 创建数据库对象**

`001_schemas.sql` 创建 `raw`、`staging`、`warehouse`、`marts` 和 `audit`。`002_ingestion_runs.sql` 创建 `audit.ingestion_runs`，字段包含 `run_id UUID`、`started_at`、`finished_at`、`status`、`source_file`、`row_count` 和 `error_message`。

- [ ] **Step 4: 运行集成验证**

Run:

```powershell
docker compose up -d db
.\.venv\Scripts\python scripts/bootstrap_db.py
docker compose exec db psql -U analytics -d olist -c '\dn'
```

Expected: 输出五个项目 Schema。

- [ ] **Step 5: 测试并提交**

Run: `python -m pytest tests/test_database.py -v`  
Expected: PASS。

```powershell
git add src/database.py sql/bootstrap scripts/bootstrap_db.py tests/test_database.py
git commit -m 'feat: bootstrap analytics database schemas'
```

**验收产出：** 数据库可以重复初始化，导入批次有独立审计表。

---

### Task 4（Day 5）: 实现原始数据导入与质量报告

**学习目标：** 理解幂等导入、批次审计、结构检查和失败回滚。

**Files:**
- Create: `src/validation/__init__.py`
- Create: `src/validation/checks.py`
- Create: `src/ingestion/loader.py`
- Create: `scripts/load_raw.py`
- Create: `tests/validation/test_checks.py`
- Create: `tests/ingestion/test_loader.py`

**Interfaces:**
- Produces: `validate_frame(frame, contract) -> ValidationReport`、`load_dataset(engine, path, contract) -> LoadResult`。

- [ ] **Step 1: 写结构缺失和主键重复测试**

```python
import pandas as pd

from src.ingestion.contracts import get_contract
from src.validation.checks import validate_frame


def test_validation_reports_missing_columns():
    frame = pd.DataFrame({'order_id': ['o1']})
    report = validate_frame(frame, get_contract('orders'))
    assert 'customer_id' in report.missing_columns
    assert report.is_valid is False


def test_validation_reports_duplicate_primary_keys():
    frame = pd.DataFrame({
        'order_id': ['o1', 'o1'],
        'customer_id': ['c1', 'c1'],
        'order_status': ['delivered', 'delivered'],
    })
    report = validate_frame(frame, get_contract('orders'))
    assert report.duplicate_primary_key_rows == 2
```

- [ ] **Step 2: 实现验证报告**

```python
from dataclasses import dataclass

import pandas as pd

from src.ingestion.contracts import DatasetContract


@dataclass(frozen=True)
class ValidationReport:
    missing_columns: tuple[str, ...]
    duplicate_primary_key_rows: int

    @property
    def is_valid(self) -> bool:
        return not self.missing_columns and self.duplicate_primary_key_rows == 0


def validate_frame(
    frame: pd.DataFrame,
    contract: DatasetContract,
) -> ValidationReport:
    missing = tuple(sorted(set(contract.columns) - set(frame.columns)))
    duplicates = 0
    if not missing and contract.primary_key:
        duplicates = int(frame.duplicated(list(contract.primary_key), keep=False).sum())
    return ValidationReport(missing, duplicates)
```

- [ ] **Step 3: 实现批次导入**

`load_dataset` 使用 `pandas.read_csv` 读取文件，先验证结构，再在同一事务中写入 `raw.<name>` 和审计结果。相同文件内容通过 SHA-256 识别；重复批次返回 `skipped`，结构错误返回失败报告且不创建半张表。

- [ ] **Step 4: 加入业务质量检查**

至少输出：每表行数、主键重复数、关键字段缺失率、孤儿外键数、负金额数、未知订单状态数、购买时间晚于送达时间的记录数。报告保存到 `artifacts/quality/latest.json`。

- [ ] **Step 5: 全量导入与验收**

Run:

```powershell
.\.venv\Scripts\python scripts/load_raw.py --data-dir data/raw
.\.venv\Scripts\python -m pytest tests/validation tests/ingestion -v
```

Expected: 九张表均被识别；严重结构错误为 0；第二次运行报告 `skipped`；测试全部 PASS。

- [ ] **Step 6: 学习复盘并提交**

在 `docs/learning/week-1.md` 回答：“为什么 CSV 行数正确仍不代表数据正确？”并记录至少三个实际发现。

Commit: `git commit -m 'feat: add audited raw data ingestion'`。

**第1周验收：** 从空数据库运行 bootstrap 和 load 命令后，九张 raw 表与质量报告可重复生成。

---

### Task 5（Day 6–7）: 构建 staging、维度表和事实表

**学习目标：** 掌握数据粒度、星型模型、代理键、去重和金额重复计算风险。

**Files:**
- Create: `sql/staging/010_staging.sql`
- Create: `sql/warehouse/020_dimensions.sql`
- Create: `sql/warehouse/021_facts.sql`
- Create: `scripts/build_warehouse.py`
- Create: `tests/sql/test_warehouse_invariants.py`

**Interfaces:**
- Produces: `warehouse.dim_customer`、`dim_product`、`dim_seller`、`dim_date`、`fact_orders`、`fact_order_items`、`fact_payments`、`fact_reviews`。

- [ ] **Step 1: 写仓库不变量测试**

```python
from sqlalchemy import text


def test_fact_orders_has_one_row_per_order(db_connection):
    result = db_connection.execute(text(
        'select count(*) = count(distinct order_id) '
        'from warehouse.fact_orders'
    )).scalar_one()
    assert result is True


def test_order_item_revenue_matches_staging(db_connection):
    query = text('''
        select abs(
          (select sum(price) from warehouse.fact_order_items) -
          (select sum(price) from staging.order_items)
        ) < 0.01
    ''')
    assert db_connection.execute(query).scalar_one() is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/sql/test_warehouse_invariants.py -v`  
Expected: FAIL，因为 warehouse 表尚未创建。

- [ ] **Step 3: 实现 staging**

在 `010_staging.sql` 中显式转换金额和时间字段、标准化状态与州代码、保留源主键、增加 `is_delivery_late` 和数据异常标志。地理位置按邮编前缀聚合代表经纬度，避免一对多连接放大。

- [ ] **Step 4: 实现维度和事实表**

`dim_customer` 以 `customer_unique_id` 为业务键；`fact_orders` 保持订单粒度；`fact_order_items` 保持订单商品粒度；支付与评价不提前丢失原始序号。建立主键、必要索引和外键。

- [ ] **Step 5: 添加金额防重复测试**

增加测试证明：先分别聚合商品与支付再连接时，订单数和总额不变化；构造一个包含两个商品和两次支付的小样本，错误连接会产生四行，正确查询仍返回一笔订单。

- [ ] **Step 6: 构建并验收**

Run:

```powershell
.\.venv\Scripts\python scripts/build_warehouse.py
.\.venv\Scripts\python -m pytest tests/sql/test_warehouse_invariants.py -v
```

Expected: 所有不变量 PASS。

- [ ] **Step 7: 提交**

Commit: `git commit -m 'feat: build typed dimensional warehouse'`。

**验收产出：** 能在面试中用一张粒度表解释每个事实表一行代表什么，以及为什么金额没有重复。

---

### Task 6（Day 8）: 建立指标字典和月度增长集市

**学习目标：** 掌握指标口径、窗口函数、新老客户定义和增长拆解。

**Files:**
- Create: `configs/metrics.yml`
- Create: `src/analytics/__init__.py`
- Create: `src/analytics/metrics.py`
- Create: `sql/marts/030_monthly_growth.sql`
- Create: `tests/analytics/test_metrics.py`
- Create: `tests/sql/test_monthly_growth.py`

**Interfaces:**
- Produces: `MetricDefinition`、`get_metric_definition(name)` 和 `marts.monthly_growth`。

- [ ] **Step 1: 写指标注册测试**

```python
from src.analytics.metrics import get_metric_definition


def test_repeat_rate_definition_contains_denominator_rule():
    metric = get_metric_definition('repeat_rate_90d')
    assert metric.unit == 'percent'
    assert '完整90天观察期' in metric.denominator
```

- [ ] **Step 2: 实现指标定义**

`MetricDefinition` 包含 `name`、`label`、`description`、`formula`、`unit`、`grain`、`filters` 和 `denominator`。从 `configs/metrics.yml` 加载 GMV、商品销售额、订单、客户、客单价、新客户、老客户、30/60/90 天复购率和延迟率。

- [ ] **Step 3: 编写月度增长 SQL**

使用 CTE 先得到客户首次有效购买月，再计算每月商品销售额、实付金额、订单、客户、新老客户及其收入。使用 `LAG` 计算环比；不完整边界月份增加 `is_complete_month` 标志。

- [ ] **Step 4: 写可核算的小样本测试**

固定三位客户、四笔订单，验证第二个月新客户数为 1、老客户数为 1、订单数为 2，并验证 AOV 的分母是订单数。

- [ ] **Step 5: 运行并提交**

Run: `python -m pytest tests/analytics/test_metrics.py tests/sql/test_monthly_growth.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: add governed growth metrics'`。

---

### Task 7（Day 9）: 构建 Cohort 与 30/60/90 天复购分析

**学习目标：** 理解 Cohort、观察窗口、右删失和分母偏差。

**Files:**
- Create: `sql/marts/031_cohort_retention.sql`
- Create: `src/analytics/retention.py`
- Create: `tests/analytics/test_retention.py`

**Interfaces:**
- Produces: `build_retention_matrix(frame) -> DataFrame` 和 `marts.cohort_retention`。

- [ ] **Step 1: 写观察期边界测试**

```python
import pandas as pd

from src.analytics.retention import eligible_for_horizon


def test_customer_without_full_horizon_is_excluded():
    first_purchase = pd.Timestamp('2018-07-01')
    data_end = pd.Timestamp('2018-08-31')
    assert eligible_for_horizon(first_purchase, data_end, days=90) is False
```

- [ ] **Step 2: 实现时间资格函数**

```python
import pandas as pd


def eligible_for_horizon(
    first_purchase: pd.Timestamp,
    data_end: pd.Timestamp,
    days: int,
) -> bool:
    return first_purchase + pd.Timedelta(days=days) <= data_end
```

- [ ] **Step 3: 编写 Cohort SQL**

对每个 `customer_unique_id` 计算首购日期和后续订单天数；分别计算 30、60、90 天复购标志。每个比例只使用拥有完整对应观察期的客户作为分母。

- [ ] **Step 4: 输出分析结果**

生成 Cohort 热力矩阵、复购时间分布和三个观察窗口的置信区间。记录至少一个“看似下降但由观察期不足造成”的反例。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/analytics/test_retention.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: add censoring-aware retention analysis'`。

---

### Task 8（Day 10）: 构建 Customer 360、RFM 与客户策略

**学习目标：** 掌握客户分析宽表、分位数分箱、集中度和分群可解释性。

**Files:**
- Create: `sql/marts/032_customer_360.sql`
- Create: `src/analytics/segmentation.py`
- Create: `tests/analytics/test_segmentation.py`

**Interfaces:**
- Produces: `assign_rfm_segments(frame, as_of_date) -> DataFrame` 和 `marts.customer_360`。

- [ ] **Step 1: 写 RFM 方向测试**

```python
import pandas as pd

from src.analytics.segmentation import score_recency


def test_lower_recency_receives_higher_score():
    recency = pd.Series([5, 50, 200], index=['a', 'b', 'c'])
    scores = score_recency(recency, bins=3)
    assert scores['a'] > scores['c']
```

- [ ] **Step 2: 实现稳定分箱**

处理大量 Frequency 等于 1 导致 `qcut` 边界重复的问题。Recency、Frequency、Monetary 分别保留原始值与分数；分群规则集中在映射表中，不散落在页面代码。

- [ ] **Step 3: 构建 Customer 360**

每个客户一行，至少包括首购、最近购买、订单数、商品金额、实付、运费、品类数、平均评分、平均延迟、90 天复购标志和数据可用时点。

- [ ] **Step 4: 形成客户策略表**

为高价值、潜力、需关注和一次性低价值客户分别定义可解释条件、客户数、收入贡献和运营建议。报告 Frequency 低变异带来的限制。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/analytics/test_segmentation.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: add customer 360 and RFM segmentation'`。

---

### Task 9（Day 11）: 商品、履约与统计证据

**学习目标：** 从描述统计进入假设检验、效应量和多因素解释。

**Files:**
- Create: `sql/marts/033_product_performance.sql`
- Create: `sql/marts/034_delivery_experience.sql`
- Create: `src/analytics/statistics.py`
- Create: `tests/analytics/test_statistics.py`
- Create: `docs/analysis/findings.md`

**Interfaces:**
- Produces: `compare_groups(values, groups) -> GroupComparison`。

- [ ] **Step 1: 写统计接口测试**

```python
import numpy as np

from src.analytics.statistics import compare_binary_groups


def test_group_comparison_reports_effect_direction():
    result = compare_binary_groups(
        values=np.array([1.0, 2.0, 8.0, 9.0]),
        groups=np.array([0, 0, 1, 1]),
    )
    assert result.group_one_median > result.group_zero_median
    assert 0.0 <= result.p_value <= 1.0
```

- [ ] **Step 2: 实现统计结果对象**

结果包含样本量、中位数或比例、绝对差、相对差、置信区间、检验名称和 p 值。连续偏态数据默认 Mann–Whitney U；分类变量默认卡方或 Fisher 检验；报告效应量而不是只报告显著性。

- [ ] **Step 3: 构建商品与履约集市**

先在订单级聚合商品、支付和物流，再关联客户复购标志。输出品类销售、运费率、延迟率、评分、复购率和样本量。

- [ ] **Step 4: 撰写第一版业务发现**

`docs/analysis/findings.md` 至少包含三条发现，每条使用“现象—证据—限制—行动建议”结构，并明确使用“相关”而非“导致”，除非设计支持因果识别。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/analytics/test_statistics.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: add product and delivery evidence analysis'`。

**数据分析集市验收（Day 11）：** 可以用 SQL 和统计证据回答增长来源、复购表现、客户价值和履约体验四类问题。

---

### Task 10（Day 12–13）: 构建 Streamlit 分析 Dashboard

**学习目标：** 掌握缓存、筛选器状态、业务叙事和可复用图表组件。

**Files:**
- Create: `app/Home.py`
- Create: `app/components/filters.py`
- Create: `app/components/kpis.py`
- Create: `app/pages/1_经营总览.py`
- Create: `app/pages/2_增长诊断.py`
- Create: `app/pages/3_留存复购.py`
- Create: `app/pages/4_客户价值.py`
- Create: `app/pages/5_商品与履约.py`
- Create: `src/analytics/repository.py`
- Create: `src/visualization/charts.py`
- Create: `tests/visualization/test_charts.py`

**Interfaces:**
- Produces: `AnalyticsRepository` 和返回 Plotly Figure 的纯图表函数。

- [ ] **Step 1: 写图表输入测试**

```python
import pandas as pd

from src.visualization.charts import line_chart


def test_line_chart_uses_requested_columns():
    frame = pd.DataFrame({'month': ['2024-01'], 'revenue': [100.0]})
    figure = line_chart(frame, x='month', y='revenue', title='Revenue')
    assert figure.data[0].x[0] == '2024-01'
    assert figure.data[0].y[0] == 100.0
```

- [ ] **Step 2: 建立只读分析仓库**

`AnalyticsRepository` 使用参数化 SQL，提供 `monthly_growth(filters)`、`cohort_retention(filters)`、`customer_segments(filters)`、`product_performance(filters)` 和 `delivery_experience(filters)`。页面不得直接创建数据库连接或拼接用户输入。

- [ ] **Step 3: 建立页面骨架和共享筛选器**

统一日期、州、品类筛选；默认排除不完整月份；使用 `st.cache_data` 缓存查询结果，并把筛选值作为缓存键。

- [ ] **Step 4: 实现五个分析页面**

每页必须包含 KPI、主图、分解图、口径说明和“分析结论”文本区。空数据时显示原因和恢复建议，不显示异常堆栈。

- [ ] **Step 5: 运行测试与手工验收**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/visualization -v
.\.venv\Scripts\streamlit run app/Home.py
```

Expected: 五个页面可打开；筛选后 KPI 和图表同步变化；无重复金额；空筛选不崩溃。

- [ ] **Step 6: 提交**

Commit: `git commit -m 'feat: deliver interactive analytics dashboard'`。

---

### Task 11（Day 14）: 构建时间安全的机器学习数据集

**学习目标：** 掌握 prediction time、feature availability、label horizon 和时间泄漏。

**Files:**
- Create: `sql/marts/035_ml_customer_features.sql`
- Create: `src/ml/__init__.py`
- Create: `src/ml/dataset.py`
- Create: `tests/ml/test_dataset.py`

**Interfaces:**
- Produces: `build_training_frame(frame, data_end, horizon_days=90) -> TrainingFrame` 和 `temporal_split(frame, train_end, valid_end)`。

- [ ] **Step 1: 写标签与边界测试**

```python
import pandas as pd

from src.ml.dataset import make_repurchase_label


def test_purchase_inside_90_days_is_positive():
    prediction_time = pd.Timestamp('2018-01-01')
    purchases = pd.Series(pd.to_datetime(['2018-03-15']))
    assert make_repurchase_label(prediction_time, purchases, 90) == 1


def test_purchase_after_90_days_is_negative():
    prediction_time = pd.Timestamp('2018-01-01')
    purchases = pd.Series(pd.to_datetime(['2018-05-01']))
    assert make_repurchase_label(prediction_time, purchases, 90) == 0
```

- [ ] **Step 2: 实现标签函数**

```python
import pandas as pd


def make_repurchase_label(
    prediction_time: pd.Timestamp,
    later_purchases: pd.Series,
    horizon_days: int,
) -> int:
    end = prediction_time + pd.Timedelta(days=horizon_days)
    return int(((later_purchases > prediction_time) & (later_purchases <= end)).any())
```

- [ ] **Step 3: 构建 ML 集市**

一位客户一行；prediction time 为首单实际送达时间；只保留该时点已知特征；末端无完整 90 天观察期的样本标记为不可训练；生成 `feature_available_at` 审计字段。

- [ ] **Step 4: 实现时间切分**

按 prediction time 排序，以固定日期切分训练、验证和测试；断言 `max(train.time) < min(valid.time)` 且 `max(valid.time) < min(test.time)`。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/ml/test_dataset.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: build leakage-safe repurchase dataset'`。

---

### Task 12（Day 15）: 建立业务基线和 Logistic Regression

**学习目标：** 理解类别不平衡、Pipeline、基线和 Top-K 业务评估。

**Files:**
- Create: `src/ml/evaluate.py`
- Create: `src/ml/train.py`
- Create: `tests/ml/test_evaluate.py`
- Create: `scripts/train_model.py`

**Interfaces:**
- Produces: `evaluate_probabilities(y_true, probabilities, top_fraction) -> ModelMetrics` 和 `train_candidates(training_frame) -> TrainingResult`。

- [ ] **Step 1: 写 Lift@K 测试**

```python
import numpy as np

from src.ml.evaluate import lift_at_fraction


def test_perfect_ranking_has_lift_above_one():
    y_true = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0])
    assert lift_at_fraction(y_true, scores, fraction=0.2) == 5.0
```

- [ ] **Step 2: 实现评估函数**

计算 prevalence、PR-AUC、ROC-AUC、Precision@K、Recall@K、Lift@K 和 Brier score。Top-K 至少保留一行，并对空数组和单类别测试集抛出清晰错误。

- [ ] **Step 3: 建立两类基线**

业务规则按首单金额、延迟或评分排序；Logistic Regression 使用 `ColumnTransformer`、缺失值填充、OneHotEncoder 和 `class_weight='balanced'`。所有转换都包含在同一 Pipeline。

- [ ] **Step 4: 输出模型比较表**

`scripts/train_model.py` 将数据时间范围、样本量、阳性率和全部指标写入 `artifacts/models/model_comparison.json`。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/ml/test_evaluate.py tests/ml/test_dataset.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: establish repurchase model baselines'`。

---

### Task 13（Day 16）: 比较提升模型、校准概率并解释结果

**学习目标：** 掌握模型选择、早停、校准、SHAP 和时间稳定性。

**Files:**
- Modify: `src/ml/train.py`
- Create: `src/ml/explain.py`
- Create: `tests/ml/test_train.py`
- Create: `docs/ml/model-card.md`

**Interfaces:**
- Produces: `artifacts/models/repurchase_pipeline.joblib`、`feature_schema.json` 和模型卡。

- [ ] **Step 1: 写训练产物测试**

```python
from pathlib import Path

from src.ml.train import save_training_result


def test_training_result_writes_pipeline_and_metadata(tmp_path, fitted_result):
    save_training_result(fitted_result, tmp_path)
    assert (tmp_path / 'repurchase_pipeline.joblib').exists()
    assert (tmp_path / 'feature_schema.json').exists()
    assert (tmp_path / 'metrics.json').exists()
```

- [ ] **Step 2: 加入 Random Forest 与 LightGBM**

所有候选使用相同训练、验证和测试时间段。只在验证集选择模型和阈值，最终测试集只评估一次。若 LightGBM 在当前 Python 环境不可安装，记录原因并使用 `HistGradientBoostingClassifier`，不得因此停掉项目。

- [ ] **Step 3: 校准和解释**

对候选最佳模型使用独立验证区间做 sigmoid 或 isotonic 校准；保存校准曲线数据。输出全局特征重要性和五个代表客户的局部解释。

- [ ] **Step 4: 编写模型卡**

模型卡包含任务、预测时点、标签、数据时间、排除规则、特征、切分、指标、阈值、限制、公平性风险和不适用场景。

- [ ] **Step 5: 验证并提交**

Run: `python -m pytest tests/ml -v`  
Expected: PASS。

Commit: `git commit -m 'feat: select and document calibrated repurchase model'`。

**模型验收（Day 16）：** 测试集结果优于业务排序基线，或如实说明未优于基线及原因；无论结果如何都保留严谨实验。

---

### Task 14（Day 17）: 营销 ROI 模拟器和预测页面

**学习目标：** 将模型分数转换为资源约束下的业务决策。

**Files:**
- Create: `src/ml/simulator.py`
- Create: `tests/ml/test_simulator.py`
- Create: `app/pages/6_复购预测.py`

**Interfaces:**
- Produces: `simulate_campaign(inputs: CampaignInputs) -> CampaignOutcome`。

- [ ] **Step 1: 写 ROI 公式测试**

```python
from src.ml.simulator import CampaignInputs, simulate_campaign


def test_campaign_roi_uses_incremental_profit_minus_contact_cost():
    outcome = simulate_campaign(CampaignInputs(
        customers=100,
        contact_cost=2.0,
        expected_conversion_lift=0.05,
        average_order_value=200.0,
        gross_margin=0.30,
    ))
    assert outcome.incremental_orders == 5.0
    assert outcome.incremental_profit == 300.0
    assert outcome.total_cost == 200.0
    assert outcome.roi == 0.5
```

- [ ] **Step 2: 实现模拟器**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignInputs:
    customers: int
    contact_cost: float
    expected_conversion_lift: float
    average_order_value: float
    gross_margin: float


@dataclass(frozen=True)
class CampaignOutcome:
    incremental_orders: float
    incremental_revenue: float
    incremental_profit: float
    total_cost: float
    roi: float


def simulate_campaign(inputs: CampaignInputs) -> CampaignOutcome:
    orders = inputs.customers * inputs.expected_conversion_lift
    revenue = orders * inputs.average_order_value
    profit = revenue * inputs.gross_margin
    cost = inputs.customers * inputs.contact_cost
    roi = (profit - cost) / cost if cost else float('inf')
    return CampaignOutcome(orders, revenue, profit, cost, roi)
```

- [ ] **Step 3: 构建预测页面**

页面展示模型卡摘要、测试指标、Top-K 客户、概率分布、主要影响因素和模拟器。所有转化提升输入标注为用户假设；下载文件不包含原始敏感文本。

- [ ] **Step 4: 验证并提交**

Run: `python -m pytest tests/ml/test_simulator.py -v`  
Expected: PASS。

Commit: `git commit -m 'feat: connect repurchase scores to campaign decisions'`。

---

### Task 15（Day 18）: 构建兼容模型客户端与安全 SQL 工具

**学习目标：** 理解 function calling、协议适配、AST 校验和最小权限。

**Files:**
- Create: `src/agent/__init__.py`
- Create: `src/agent/client.py`
- Create: `src/agent/safety.py`
- Create: `src/agent/tools.py`
- Create: `tests/agent/test_safety.py`
- Create: `tests/agent/test_tools.py`

**Interfaces:**
- Produces: `LLMClient.complete(messages, tools) -> LLMResponse`、`validate_read_only_sql(sql, allowed_views) -> str`、`AnalysisTools`。

- [ ] **Step 1: 写 SQL 安全测试**

```python
import pytest

from src.agent.safety import UnsafeQueryError, validate_read_only_sql


def test_allowed_select_is_accepted():
    sql = 'select month, revenue from marts.monthly_growth limit 10'
    assert validate_read_only_sql(sql, {'marts.monthly_growth'}) == sql


@pytest.mark.parametrize('sql', [
    'delete from marts.monthly_growth',
    'select * from raw.orders',
    'select 1; drop table warehouse.fact_orders',
])
def test_unsafe_sql_is_rejected(sql):
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql, {'marts.monthly_growth'})
```

- [ ] **Step 2: 实现 AST 校验**

使用 `sqlglot.parse` 要求只有一棵语法树；拒绝 Insert、Update、Delete、Drop、Create、Alter、Command 和非白名单 Table；无 LIMIT 时增加默认 500 行，上限 2000 行。

- [ ] **Step 3: 实现模型适配器**

`OpenAICompatibleClient` 从 Settings 初始化 `OpenAI(api_key=..., base_url=...)`，将内部 `ToolDefinition` 转换为兼容工具 Schema，并把文本、工具调用、参数错误统一转换为 `LLMResponse`。

- [ ] **Step 4: 实现五个工具**

`AnalysisTools` 注册 `get_metric_definition`、`run_safe_sql`、`create_chart`、`predict_repurchase`、`simulate_campaign`。数据库工具设置只读事务、statement timeout 和最大返回行数。

- [ ] **Step 5: 测试并提交**

Run: `python -m pytest tests/agent/test_safety.py tests/agent/test_tools.py -v`  
Expected: PASS，所有写入和越权查询被拒绝。

Commit: `git commit -m 'feat: add provider-neutral guarded analysis tools'`。

---

### Task 16（Day 19）: 实现 Agent 循环、评测集和 Streamlit 问数页面

**学习目标：** 掌握工具循环、停止条件、可审计轨迹和 Agent 评测。

**Files:**
- Create: `src/agent/orchestrator.py`
- Create: `src/agent/evaluation.py`
- Create: `configs/agent_questions.yml`
- Create: `tests/agent/test_orchestrator.py`
- Create: `app/pages/7_AI分析助手.py`
- Create: `scripts/evaluate_agent.py`

**Interfaces:**
- Produces: `AnalysisAgent.run(question: str) -> AgentAnswer` 和 `evaluate_agent(cases) -> EvaluationReport`。

- [ ] **Step 1: 写工具循环测试**

```python
from src.agent.orchestrator import AnalysisAgent


def test_agent_executes_tool_then_returns_audited_answer(
    fake_client,
    fake_tools,
):
    agent = AnalysisAgent(fake_client, fake_tools, max_steps=4)
    answer = agent.run('最近一个完整月的销售额是多少？')
    assert answer.tool_trace[0].name == 'get_metric_definition'
    assert answer.tool_trace[1].name == 'run_safe_sql'
    assert answer.sql
    assert answer.data_range
```

- [ ] **Step 2: 实现有界 Agent 循环**

每轮只接受已注册工具；Pydantic 校验参数；工具异常返回结构化错误供模型修正；最多 6 步；连续两次相同失败立即停止；最终答案必须包含结论、证据、指标口径、时间范围和限制。

- [ ] **Step 3: 建立 30 个黄金问题**

`configs/agent_questions.yml` 覆盖增长、留存、客户、商品、履约、预测、不可回答和恶意 SQL。每题保存允许的指标、期望数值或结果哈希、容差和是否应拒绝。

- [ ] **Step 4: 实现评测**

输出工具选择正确率、SQL 执行成功率、数值准确率、拒绝正确率、平均延迟和估算调用成本到 `artifacts/agent/evaluation.json`。CI 使用 fake client；真实 API 评测由显式命令触发，避免自动花费。

- [ ] **Step 5: 构建问数页面**

页面显示问题、答案、结果表、Plotly 图表、SQL、指标定义、时间范围和折叠的工具轨迹。没有 API Key 时加载固定演示问答，不伪装为实时结果。

- [ ] **Step 6: 验证并提交**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/agent -v
.\.venv\Scripts\python scripts/evaluate_agent.py --mode fake
```

Expected: 测试 PASS；恶意 SQL 拒绝率 100%；报告文件生成。

Commit: `git commit -m 'feat: deliver evaluated analytics agent'`。

---

### Task 17（Day 20）: 全链路验收、文档、部署与面试材料

**学习目标：** 掌握可复现交付、回归验证和面试叙事。

**Files:**
- Create: `README.md`
- Create: `docs/data-dictionary.md`
- Create: `docs/metric-dictionary.md`
- Create: `docs/architecture.md`
- Create: `docs/interview-guide.md`
- Create: `docs/retrospectives/final.md`
- Create: `scripts/verify_project.py`
- Create: `tests/integration/test_end_to_end.py`
- Modify: `docker-compose.yml`

**Interfaces:**
- Produces: 一条可重复的项目验证命令和完整作品集材料。

- [ ] **Step 1: 写最小端到端测试**

```python
def test_core_artifacts_exist(project_root):
    required = [
        'artifacts/quality/latest.json',
        'artifacts/models/repurchase_pipeline.joblib',
        'artifacts/models/metrics.json',
        'artifacts/agent/evaluation.json',
    ]
    for relative_path in required:
        assert (project_root / relative_path).exists()
```

- [ ] **Step 2: 创建统一验证脚本**

`verify_project.py` 依次检查环境变量、数据库健康、源文件、Schema、数据质量、核心指标、模型产物、Agent 评测和测试结果；任一步失败返回非零退出码并打印修复建议。

- [ ] **Step 3: 完成 README**

README 必须包含：一句话价值、三条核心发现、截图、架构、数据来源、快速启动、项目结构、指标口径、模型结果、Agent 安全与评测、限制和复现命令。不得把“高准确率”作为主要卖点。

- [ ] **Step 4: 完成专业文档**

数据字典记录表粒度、主键和字段；指标字典与 `metrics.yml` 一致；架构文档解释数据流；面试指南准备 3 分钟和 10 分钟讲法，以及至少十个追问答案。

- [ ] **Step 5: 全链路验证**

Run:

```powershell
docker compose up -d
.\.venv\Scripts\python scripts/verify_project.py
.\.venv\Scripts\python -m pytest -v
.\.venv\Scripts\python -m ruff check src tests app scripts
```

Expected: 验证脚本退出码 0；测试全部 PASS；Ruff 无错误；Dashboard 可访问。

- [ ] **Step 6: 最终复盘**

`docs/retrospectives/final.md` 回答：最重要的业务发现、最危险的数据错误、模型为何使用时间切分、Agent 如何保证安全、如果再做两周会改进什么。

- [ ] **Step 7: 最终提交**

```powershell
git add README.md docs scripts tests docker-compose.yml
git commit -m 'docs: complete portfolio delivery and interview guide'
git status --short
```

Expected: 工作区干净。

**最终验收：** 从 README 可以复现项目；Dashboard 能讲清业务问题；机器学习有时间安全的评估；Agent 有安全与准确性证据；面试材料能解释所有关键取舍。

---

## 每周教学检查点

### 第1周复盘问题

- 一张事实表的“粒度”是什么意思？
- 为什么订单商品和支付不能直接连接后求和？
- 幂等导入与普通脚本重复运行有什么区别？
- 数据契约和数据质量检查分别解决什么问题？

### 第2周复盘问题

- 新客户、老客户和复购客户的分母分别是什么？
- 为什么数据末端会低估 90 天复购率？
- p 值、效应量和业务价值有什么区别？
- 哪三条结论有最充分的证据，哪些只能算假设？

### 第3周复盘问题

- prediction time、feature window 和 label window 分别是什么？
- 为什么随机切分可能产生时间泄漏？
- 为什么 PR-AUC 和 Lift@10% 比 Accuracy 更适合本项目？
- 模型分数如何转化为营销资源分配？

### 第4周复盘问题

- 为什么 Agent 不应直接拥有数据库写权限？
- AST 校验和数据库只读账号为什么需要同时存在？
- 如何证明 Agent 的答案准确，而不只是看起来合理？
- 如果 API 不可用，项目为何仍然可以演示？

## 简历成果模板

最终数值必须由实际运行结果替换，禁止预填虚构指标。中文模板：

> 基于 Olist 约 10 万笔多表电商交易构建 Python + PostgreSQL 分层分析平台，统一增长、Cohort 留存、RFM 与履约指标口径，并通过 Streamlit 提供交互式决策看板；采用严格时间窗口训练复购倾向模型，以 PR-AUC、Lift@10% 和概率校准评估营销筛选价值；实现带 SQL AST 校验、只读权限和固定问数评测的自然语言分析 Agent。

## 每日工作方式

每天开始先阅读对应 Task 的“学习目标”和测试；实现时一次只处理一个复选框；每个测试先确认失败原因正确，再写最小实现；每天结束运行相关测试、填写学习笔记并提交。遇到数据结果与预期不一致时暂停页面开发，先追查粒度、分母、时间窗口和过滤条件。
