# Day 20：本地可复现作品集交付设计

## 目标

将现有 Olist 数据分析、机器学习与受控 Agent 项目整理为可在本地复现、可验收、可用于中英文答辩的作品集交付。交付重点是验证现有状态与清楚说明恢复路径，不在验证过程中重建数据库、训练模型或调用真实大语言模型。

## 范围与非目标

本日交付统一验证脚本、中英双语 README、数据字典、指标字典、架构说明、面试指南和最终复盘，并让 Docker Compose 能在不同电脑上选择本地 PostgreSQL 数据卷。

本日不部署公网服务，不提交 Olist 原始 CSV，不自动下载 Kaggle 数据，不自动导入或重建数据库，不自动训练模型，也不在验收中调用配置于 `.env` 的真实模型服务。

## 本地运行与 Docker 卷

Docker 只负责 PostgreSQL；Streamlit 使用本机 Python 3.13 运行。默认 Compose 卷名为 `data_analysis_postgres_data`，适用于新电脑首次初始化。`POSTGRES_VOLUME_NAME` 可在本地 `.env` 覆盖卷名，用于继续使用已存在的数据库卷；该环境特定值不写入 Git。

从零复现时，使用者先按 `data/README.md` 下载九份 Olist CSV 至 `data/raw/`，再依次执行 bootstrap、raw 导入、warehouse 构建和 marts 构建。仓库不承诺在缺少原始 CSV 时从空库恢复事实表；验证脚本会把这种情况说明为“重建未就绪”，而不是错误声称项目损坏。

## 统一验证脚本

`scripts/verify_project.py` 提供两个模式。

- 默认模式验证 Docker 引擎可用、PostgreSQL 可连接、`raw`、`staging`、`warehouse`、`marts` schema 存在、marts 真正依赖的 6 个 raw 表与 5 个 warehouse 表就绪、关键分析集市存在、四个运行时产物非空（三个 JSON 可解析、joblib 不执行加载），并检查 `.env` 同时未追踪且仍被 Git 忽略。
- `--full` 在默认检查通过后，只对以下逐文件审计的精确清单执行带 `-v` 的 pytest：`tests/test_config.py`、`tests/agent/test_client.py`、`tests/analytics/test_metrics.py`、`tests/analytics/test_retention.py`、`tests/analytics/test_segmentation.py`、`tests/analytics/test_statistics.py`、`tests/integration/test_end_to_end.py`、`tests/integration/test_verify_project.py`、`tests/ml/test_roi.py`、`tests/validation/test_checks.py`、`tests/visualization/test_charts.py`、`tests/visualization/test_navigation.py`；随后执行 `py -3.13 -m ruff check src tests app scripts`。它明确排除 `tests/sql`、`tests/ingestion`、`tests/agent/test_evaluation.py` 及 bootstrap/load/build 入口，保留 600 秒有限超时；直接入口集成只运行 `--help`。无写入结论只适用于当前清单，任何增删都必须重新审计默认数据库、真实制品和入口副作用。
- `--require-source-data` 额外要求 `data/raw/` 中九份 CSV 均存在，面向准备从零重建的环境。

失败信息必须说明失败层级和下一步命令。缺 schema 先提示 `bootstrap_db.py`；缺 raw 必需表时指向 `data/README.md` 与 `load_raw.py --data-dir data/raw`；缺 warehouse 必需表时提示 `build_warehouse.py`；只有 raw 与 warehouse 必需表均就绪而 marts 表缺失时才提示 `build_marts.py`。缺失模型或评测产物提示对应训练或 fake 评测命令。脚本不泄露数据库密码、LLM Key 或完整连接串。

四个产物采用 `generated-after-clone` 策略。仓库跟踪 `artifacts/manifest.json`，逐项声明路径、精确生成命令和前置条件；端到端源码验收验证 manifest，不要求干净 checkout 已存在被忽略的运行时输出。运行时 verifier 仍要求实际产物可用。

## 文档交付

README 使用中英双语段落，覆盖项目价值、已验证的业务发现、数据来源、快速启动、项目结构、Dashboard、机器学习、Agent 安全与评测、限制和完整复现路径。英文内容与中文内容表达相同事实，不把 fake 评测 100% 写成真实模型准确率。

`docs/data-dictionary.md` 记录 raw、staging、warehouse 与 marts 中交付相关表的粒度、主键、来源及关键字段；`docs/metric-dictionary.md` 以现有指标注册与集市 SQL 为依据定义 GMV、商品金额、订单数、客户数、延迟率、评分和 90 天复购率，并写明过滤条件和分母。

90 天复购必须区分两种真实口径：`customer_360` 及商品/履约分析使用首购 `purchased_at` 起算、观察至 delivered 数据终点 `MAX(purchased_at)` 的 purchase-anchored 标签；`ml_customer_features` 则以首笔已送达订单的送达时间为 `prediction_time`，再检查后续 delivered 订单的 `purchased_at` 是否落入 90 天的 delivery-anchored 标签。任何文档都不得把其中一种写成通用定义。

`docs/architecture.md` 使用 Mermaid 描述 CSV、分层数仓、分析集市、Dashboard、机器学习和 Agent 的单向数据流，解释金额预聚合、时间安全标签、只读 SQL 与审计轨迹。`docs/interview-guide.md` 提供中英文 3 分钟和 10 分钟项目讲述，以及至少十个技术追问与如实回答。`docs/retrospectives/final.md` 记录关键业务发现、最危险的数据错误、模型时间切分、Agent 安全边界、真实模型稳定性限制和下一轮改进建议。

## 测试与验收

新增端到端测试只检查版本化 artifact manifest、验证脚本和文档入口；它不要求干净 checkout 已存在生成物，也不访问 Docker、网络或真实 LLM。验证脚本自身的单元测试通过注入健康检查与命令执行器，覆盖成功、分层恢复、缺失源文件、空/损坏产物、`.env` 双重保护及安全 `--full` 命令等情况。

验收命令为：

```powershell
py -3.13 scripts/verify_project.py
py -3.13 scripts/verify_project.py --full
py -3.13 -m ruff check src tests app scripts
```

最终交付仅在验证脚本给出成功、测试与 Ruff 通过、README 的本地启动步骤可执行且 `.env` 未追踪时完成。真实模型问数只作为可选体验，不是本地作品集的验收前提。
