# Olist 电商增长、留存与复购分析平台 / Olist Growth, Retention, and Repurchase Analytics Platform

## 项目价值 / Project value

**中文。** 本项目把 Olist 的匿名化历史交易快照组织为可复现的本地分析作品集：从 CSV 数据契约、PostgreSQL 分层建模和受治理的分析集市，到 Streamlit 仪表盘、时间安全的 90 天复购排序，以及带安全边界的分析 Agent。它服务于“增长来自哪里、哪些客户值得优先触达、履约体验与评分/复购有何关联”这类决策问题，而不把历史关联或情景模拟冒充为因果营销效果。

**English.** This project turns Olist's anonymized historical transaction snapshot into a reproducible local analytics portfolio: CSV contracts, layered PostgreSQL modeling, governed marts, a Streamlit dashboard, leakage-safe 90-day repurchase ranking, and a bounded analysis Agent. It supports questions such as where growth comes from, which customers merit prioritization, and how delivery experience is associated with ratings and repurchase; it does not present historical associations or scenario simulation as causal marketing effects.

## 已验证的发现 / Verified findings

**中文。** 已送达且有评分的订单中，按时组为 88,171 单、延迟组为 7,661 单；评分中位数分别为 5 和 2，Mann–Whitney 检验的秩二列相关为 -0.554。按时首购客户的 90 天复购率为 2.027%（68,778 人中 1,394 人），延迟组为 1.816%（6,609 人中 120 人）；绝对差 -0.211 个百分点、Fisher 精确检验 p=0.251，故这不是“延迟导致流失”的因果结论。商品金额最高的 `health_beauty` 为 1,233,131.72、90 天复购率 1.951%；`bed_bath_table` 为 1,023,434.76、复购率 3.536%。这些是受既定口径约束的历史描述，不是当前 Olist 经营结果或行动收益承诺。

**English.** Among delivered orders with ratings, the on-time group has 88,171 orders and the late group has 7,661; their median ratings are 5 and 2, with a rank-biserial correlation of -0.554 from the Mann–Whitney test. The 90-day repurchase rate is 2.027% for on-time first-purchase customers (1,394 of 68,778) and 1.816% for late customers (120 of 6,609); the absolute difference is -0.211 percentage points and Fisher's exact test is p=0.251, so this is not a causal claim that lateness causes churn. The highest item-revenue category, `health_beauty`, has 1,233,131.72 in item revenue and a 1.951% 90-day repurchase rate; `bed_bath_table` has 1,023,434.76 and 3.536%. These are historical descriptions under defined metrics, not current Olist results or promised action value.

**口径说明 / Definition note.** 上述客户、商品和履约分析集市以首购 `purchased_at` 为 90 天窗口起点，并以数据终点 `MAX(purchased_at)` 判断观察期完整；这与后文 ML 的首单送达时间锚点不同。 / The customer, product, and delivery analysis marts above anchor the 90-day window on first-purchase `purchased_at` and assess completeness through data-end `MAX(purchased_at)`; this differs from the ML delivery-time anchor described below.

## 数据边界 / Data boundary

**中文。** 原始输入严格限于 Olist 发布的九个 CSV：客户、订单、订单商品、支付、评价、商品、卖家、地理位置和品类翻译。文件名、主键和列由 `src/ingestion/contracts.py` 校验；原始 CSV 不进入 Git。下载、放置和许可边界见 [data/README.md](data/README.md)。交易分析和行为指标默认仅使用 `delivered` 订单；客户身份以 `customer_unique_id` 统一，而不是订单地址层面的 `customer_id`。

**English.** Source input is strictly limited to Olist's nine published CSV files: customers, orders, order items, payments, reviews, products, sellers, geolocation, and category translation. `src/ingestion/contracts.py` validates filenames, keys, and columns; raw CSVs are not committed to Git. See [data/README.md](data/README.md) for download, placement, and licensing boundaries. Transaction analysis and behavior metrics default to `delivered` orders; customer identity is unified with `customer_unique_id`, not the address-level `customer_id`.

## 本地启动与恢复 / Local start and recovery

**中文。** 需要 Python 3.13、Docker Compose 和已配置的本地依赖。复制 `.env.example` 为未跟踪的 `.env`，按本地需要填写数据库与可选 LLM 配置；不要提交 `.env`、密钥或本地卷覆盖。启动数据库并启动仪表盘：

```powershell
docker compose up -d
py -3.13 -m streamlit run app/Home.py --server.port 8501
```

默认 PostgreSQL 卷名是 `data_analysis_postgres_data`。若要连接已有本地卷，只在未提交的 `.env` 中写入 `POSTGRES_VOLUME_NAME=已有卷名`；新环境可显式使用 `POSTGRES_VOLUME_NAME=data_analysis_postgres_data`，任何机器专用覆盖值都不得提交。 / The default PostgreSQL volume is `data_analysis_postgres_data`. To attach an existing local volume, set `POSTGRES_VOLUME_NAME=existing_volume_name` only in the untracked `.env`; a new environment may explicitly use `POSTGRES_VOLUME_NAME=data_analysis_postgres_data`. Never commit a machine-specific override.

若要从空数据库恢复，先按 [data/README.md](data/README.md) 放置九个 CSV，然后依次运行：

```powershell
py -3.13 scripts/bootstrap_db.py
py -3.13 scripts/load_raw.py --data-dir data/raw
py -3.13 scripts/build_warehouse.py
py -3.13 scripts/build_marts.py
py -3.13 scripts/run_quality_checks.py
py -3.13 scripts/train_model.py
py -3.13 scripts/evaluate_agent.py --mode fake
```

质量报告入口 `py -3.13 scripts/run_quality_checks.py` 读取现有数据库，并且只写入 `artifacts/quality/latest.json`；它不重建数据层。日常验收不需要下载 CSV、重建表、训练模型或调用 LLM：运行 `py -3.13 scripts/verify_project.py`。`py -3.13 scripts/verify_project.py --full` 只追加 `scripts/verify_project.py` 的 `FULL_COMMANDS` 中 12 个经审计的精确测试文件与 Ruff；当前清单排除 `tests/sql`、整个 `tests/ingestion` 和 `tests/agent/test_evaluation.py`。这项边界只适用于当前精确清单，不能证明任意或未来测试均不写状态；修改清单前必须重新审计数据库、真实制品和直接入口副作用。验证器同时观察 marts 真正依赖的 6 个 raw 表和 5 个 warehouse 表：缺 raw 表时指向 `data/README.md` 与 `load_raw.py --data-dir data/raw`，缺 warehouse 表时指向 `build_warehouse.py`，只有两层就绪且 marts 缺失时才指向 `build_marts.py`。准备从九份 CSV 重建时，可先运行 `py -3.13 scripts/verify_project.py --require-source-data` 检查源文件清单。若数据库未就绪，先确认 Docker 可用并重试 `docker compose up -d`；恢复流程会改动本地派生数据，应与只读验收区分。

**English.** Python 3.13, Docker Compose, and configured local dependencies are required. Copy `.env.example` to an untracked `.env`, fill in local database and optional LLM settings as needed, and never commit `.env`, secrets, or a local volume override. Start the database and dashboard with:

```powershell
docker compose up -d
py -3.13 -m streamlit run app/Home.py --server.port 8501
```

To restore an empty database, first place the nine CSVs as described in [data/README.md](data/README.md), then run:

```powershell
py -3.13 scripts/bootstrap_db.py
py -3.13 scripts/load_raw.py --data-dir data/raw
py -3.13 scripts/build_warehouse.py
py -3.13 scripts/build_marts.py
py -3.13 scripts/run_quality_checks.py
py -3.13 scripts/train_model.py
py -3.13 scripts/evaluate_agent.py --mode fake
```

The quality-report entrypoint, `py -3.13 scripts/run_quality_checks.py`, reads the existing database and writes only `artifacts/quality/latest.json`; it does not rebuild a data layer. Routine acceptance does not download CSVs, rebuild tables, train a model, or call an LLM: run `py -3.13 scripts/verify_project.py`. `py -3.13 scripts/verify_project.py --full` adds only the 12 audited exact test files recorded in `FULL_COMMANDS` plus Ruff; the current list excludes `tests/sql`, all of `tests/ingestion`, and `tests/agent/test_evaluation.py`. This boundary applies only to the current exact list and does not prove that arbitrary or future tests are non-writing; re-audit database, real-artifact, and direct-entrypoint side effects before changing it. The verifier also observes the six raw tables and five warehouse tables actually required upstream of marts: missing raw tables route to `data/README.md` and `load_raw.py --data-dir data/raw`, missing warehouse tables route to `build_warehouse.py`, and `build_marts.py` is suggested only after both layers are ready. Before rebuilding from the nine CSVs, use `py -3.13 scripts/verify_project.py --require-source-data` to check the source-file inventory. If the database is not ready, confirm Docker is available and retry `docker compose up -d`; the restore route mutates local derived data and is deliberately separate from read-only acceptance.

生成产物采用 `generated-after-clone` 策略：Git 只跟踪 [artifacts/manifest.json](artifacts/manifest.json)，其中逐项记录四个必需产物、精确生成命令和前置条件；克隆后按上面的恢复顺序生成。运行时验证器仍要求四个实际产物非空，且三个 JSON 可解析。 / Generated artifacts follow a `generated-after-clone` policy: Git tracks only [artifacts/manifest.json](artifacts/manifest.json), which records all four required outputs, their exact generation commands, and prerequisites. Generate them after cloning in the recovery order above. The runtime verifier still requires all four outputs to be non-empty and all three JSON files to parse.

## 结构与仪表盘 / Structure and dashboard

| 区域 / Area | 中文说明 | English description |
| --- | --- | --- |
| `data/` | 原始数据获取说明；CSV 不入库。 | Raw-data instructions; CSVs are not committed. |
| `sql/` | `raw → staging → warehouse → marts` 的可重建 SQL。 | Rebuildable SQL for `raw → staging → warehouse → marts`. |
| `src/` | 导入、指标、ML、Agent、安全与质量代码。 | Ingestion, metrics, ML, Agent, safety, and quality code. |
| `app/` | Streamlit 首页、共享组件与页面。 | Streamlit home page, shared components, and pages. |
| `artifacts/` | 版本化生成清单；质量、模型和 Agent fake 评测在克隆后生成并保持忽略。 | Versioned generation manifest; quality, model, and fake-Agent outputs are generated after clone and remain ignored. |
| `docs/` | 口径、架构、访谈材料和回顾。 | Definitions, architecture, interview material, and retrospective. |

**中文。** 仪表盘页面为经营总览、增长诊断、留存复购、客户价值、商品与履约、营销 ROI 模拟器和 AI 分析助手。展示层中文化；内部 DataFrame、SQL 和模型字段保留英文以保持实现一致性。默认提示并排除不完整月份，州指客户收货地址州。

**English.** Dashboard pages cover operating overview, growth diagnosis, retention and repurchase, customer value, product and fulfillment, a marketing ROI simulator, and an AI analysis assistant. The presentation layer is Chinese-localized while internal DataFrame, SQL, and model fields remain English for implementation consistency. Incomplete months are flagged and excluded by default; a state means the customer's delivery-address state.

## 时间安全的机器学习 / Leakage-safe machine learning

**中文。** `marts.ml_customer_features` 每位客户一行。`prediction_time` 是首笔已送达订单的送达时间，六个特征仅来自首单：商品件数、商品金额、运费、支付金额、配送时长和品类数。标签选择后续已送达订单，但窗口实际比较的是该后续已送达订单的 `purchased_at` 是否落在 `(prediction_time, prediction_time + 90 天]`，不是其送达时间；`eligible_for_90d` 排除观察期不足的客户。82,500 个完整样本按时间切为训练 49,500、选择 12,375、校准 4,125、最终测试 16,500；模型选择不用最终测试集。候选是 class-balanced 逻辑回归、随机森林和 LightGBM，以选择期 PR-AUC 为主、Lift@10% 为并列裁决，选中逻辑回归。最终测试中，选中模型 PR-AUC 0.012274、ROC-AUC 0.543393、Lift@10% 1.226994、Brier 0.009785；首单金额规则的 PR-AUC 为 0.009855、Lift@10% 为 0.858896。它只能帮助有限触达的排序，绝对精度较低，不能证明营销增量或因果关系。

**English.** `marts.ml_customer_features` has one row per customer. `prediction_time` is the delivery time of the first delivered order, and the six features come only from that first order: item count, item revenue, freight, payment value, delivery duration, and category count. The label selects a later delivered order, but the window actually compares that later delivered order's `purchased_at` with `(prediction_time, prediction_time + 90 days]`, not its delivery time; `eligible_for_90d` excludes customers without a complete observation window. The 82,500 complete samples are temporally split into 49,500 training, 12,375 selection, 4,125 calibration, and 16,500 final-test rows; final test data is not used for selection. Candidates are class-balanced logistic regression, random forest, and LightGBM; selection prioritizes PR-AUC with Lift@10% as a tie-breaker, and logistic regression is selected. On final test, the selected model has PR-AUC 0.012274, ROC-AUC 0.543393, Lift@10% 1.226994, and Brier 0.009785; the first-order-item-revenue rule has PR-AUC 0.009855 and Lift@10% 0.858896. It only supports ranking under limited outreach, has low absolute precision, and does not prove marketing incrementality or causality.

## Agent 边界与限制 / Agent boundaries and limitations

**中文。** Agent 只能调用受治理工具：指标定义、白名单集市上的单条 SELECT、受限图表、六个批准首单特征的复购评分，以及显式情景的 ROI 模拟。SQL 先经 SQLGlot AST 校验，只允许受批准视图、分析函数和正整数行数限制；执行器再设置只读事务、五秒超时并最多返回 2,000 行。每次调用记录工具轨迹，并对敏感参数脱敏、截断过大负载。`artifacts/agent/evaluation.json` 是 30 个 golden cases 的确定性 fake Agent 结果：它验证离线工具编排和拒绝契约，不衡量真实模型、真实数据库或真实 LLM 的准确率。真实调用须显式确认、配置密钥，并受最多 5 例、15 秒和估计成本上限约束。

**English.** The Agent may call only governed tools: metric definitions, one SELECT against allowlisted marts, bounded charts, repurchase scoring from the six approved first-order features, and ROI simulation with explicit scenarios. SQL is first validated through a SQLGlot AST: only approved views, analytical functions, and a positive integer row limit are accepted; the executor then sets a read-only transaction, a five-second timeout, and returns at most 2,000 rows. Every call records a tool trace, while sensitive arguments are redacted and oversized payloads truncated. `artifacts/agent/evaluation.json` is a deterministic fake-Agent result for 30 golden cases: it verifies offline tool-orchestration and rejection contracts, not the accuracy of a live model, live database, or live LLM. Live calls require explicit confirmation, configured credentials, and caps of five cases, fifteen seconds, and estimated cost.

## 进一步阅读 / Further reading

- [数据字典 / Data dictionary](docs/data-dictionary.md)
- [指标字典 / Metric dictionary](docs/metric-dictionary.md)
- [架构 / Architecture](docs/architecture.md)
- [面试讲稿与追问 / Interview guide](docs/interview-guide.md)
- [最终回顾 / Final retrospective](docs/retrospectives/final.md)
- [详细分析与模型报告 / Detailed analysis and ML report](docs/reports/analysis-and-machine-learning-detailed-report.md)
