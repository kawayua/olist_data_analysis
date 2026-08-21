# Olist 电商增长、留存与复购分析平台 / Olist Growth, Retention, and Repurchase Analytics Platform

## 项目价值 / Project value

**中文。** 本项目把 Olist 的匿名化历史交易快照组织为可复现的本地分析作品集：从 CSV 数据契约、PostgreSQL 分层建模和受治理的分析集市，到 Streamlit 仪表盘、时间安全的 90 天复购排序，以及带安全边界的分析 Agent。它服务于“增长来自哪里、哪些客户值得优先触达、履约体验与评分/复购有何关联”这类决策问题，而不把历史关联或情景模拟冒充为因果营销效果。

**English.** This project turns Olist's anonymized historical transaction snapshot into a reproducible local analytics portfolio: CSV contracts, layered PostgreSQL modeling, governed marts, a Streamlit dashboard, leakage-safe 90-day repurchase ranking, and a bounded analysis Agent. It supports questions such as where growth comes from, which customers merit prioritization, and how delivery experience is associated with ratings and repurchase; it does not present historical associations or scenario simulation as causal marketing effects.

## 已验证的发现 / Verified findings

**中文。** 已送达且有评分的订单中，按时组为 88,171 单、延迟组为 7,661 单；评分中位数分别为 5 和 2，Mann–Whitney 检验的秩二列相关为 -0.554。按时首购客户的 90 天复购率为 2.027%（68,778 人中 1,394 人），延迟组为 1.816%（6,609 人中 120 人）；绝对差 -0.211 个百分点、Fisher 精确检验 p=0.251，故这不是“延迟导致流失”的因果结论。商品金额最高的 `health_beauty` 为 1,233,131.72、90 天复购率 1.951%；`bed_bath_table` 为 1,023,434.76、复购率 3.536%。这些是受既定口径约束的历史描述，不是当前 Olist 经营结果或行动收益承诺。

**English.** Among delivered orders with ratings, the on-time group has 88,171 orders and the late group has 7,661; their median ratings are 5 and 2, with a rank-biserial correlation of -0.554 from the Mann–Whitney test. The 90-day repurchase rate is 2.027% for on-time first-purchase customers (1,394 of 68,778) and 1.816% for late customers (120 of 6,609); the absolute difference is -0.211 percentage points and Fisher's exact test is p=0.251, so this is not a causal claim that lateness causes churn. The highest item-revenue category, `health_beauty`, has 1,233,131.72 in item revenue and a 1.951% 90-day repurchase rate; `bed_bath_table` has 1,023,434.76 and 3.536%. These are historical descriptions under defined metrics, not current Olist results or promised action value.

## 数据边界 / Data boundary

**中文。** 原始输入严格限于 Olist 发布的九个 CSV：客户、订单、订单商品、支付、评价、商品、卖家、地理位置和品类翻译。文件名、主键和列由 `src/ingestion/contracts.py` 校验；原始 CSV 不进入 Git。下载、放置和许可边界见 [data/README.md](data/README.md)。交易分析和行为指标默认仅使用 `delivered` 订单；客户身份以 `customer_unique_id` 统一，而不是订单地址层面的 `customer_id`。

**English.** Source input is strictly limited to Olist's nine published CSV files: customers, orders, order items, payments, reviews, products, sellers, geolocation, and category translation. `src/ingestion/contracts.py` validates filenames, keys, and columns; raw CSVs are not committed to Git. See [data/README.md](data/README.md) for download, placement, and licensing boundaries. Transaction analysis and behavior metrics default to `delivered` orders; customer identity is unified with `customer_unique_id`, not the address-level `customer_id`.

## 本地启动与恢复 / Local start and recovery

**中文。** 需要 Python 3.13、Docker Compose 和已配置的本地依赖。复制 `.env.example` 为未跟踪的 `.env`，按本地需要填写数据库与可选 LLM 配置；不要提交 `.env`、密钥或本地卷覆盖。启动数据库并启动仪表盘：

```powershell
docker compose up -d
py -3.13 -m streamlit run app/Home.py --server.port 8501
```

若要从空数据库恢复，先按 [data/README.md](data/README.md) 放置九个 CSV，然后依次运行：

```powershell
py -3.13 scripts/bootstrap_db.py
py -3.13 scripts/load_raw.py --data-dir data/raw
py -3.13 scripts/build_warehouse.py
py -3.13 scripts/build_marts.py
py -3.13 scripts/train_model.py
py -3.13 scripts/evaluate_agent.py --mode fake
```

日常验收不需要下载 CSV、重建表、训练模型或调用 LLM：运行 `py -3.13 scripts/verify_project.py`。完整本地检查使用 `py -3.13 scripts/verify_project.py --full`。若数据库未就绪，先确认 Docker 可用并重试 `docker compose up -d`；恢复流程会改动本地派生数据，应与只读验收区分。

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
py -3.13 scripts/train_model.py
py -3.13 scripts/evaluate_agent.py --mode fake
```

Routine acceptance does not download CSVs, rebuild tables, train a model, or call an LLM: run `py -3.13 scripts/verify_project.py`. Use `py -3.13 scripts/verify_project.py --full` for the complete local check. If the database is not ready, confirm Docker is available and retry `docker compose up -d`; the restore route mutates local derived data and is deliberately separate from read-only acceptance.

## 结构与仪表盘 / Structure and dashboard

| 区域 / Area | 中文说明 | English description |
| --- | --- | --- |
| `data/` | 原始数据获取说明；CSV 不入库。 | Raw-data instructions; CSVs are not committed. |
| `sql/` | `raw → staging → warehouse → marts` 的可重建 SQL。 | Rebuildable SQL for `raw → staging → warehouse → marts`. |
| `src/` | 导入、指标、ML、Agent、安全与质量代码。 | Ingestion, metrics, ML, Agent, safety, and quality code. |
| `app/` | Streamlit 首页、共享组件与页面。 | Streamlit home page, shared components, and pages. |
| `artifacts/` | 已保存的质量、模型和 Agent 假评估产物。 | Saved quality, model, and Agent fake-evaluation artifacts. |
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
