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

- 默认模式验证 Docker 引擎可用、PostgreSQL 可连接、`raw`、`staging`、`warehouse`、`marts` schema 存在、关键分析集市存在、质量报告/模型产物/Agent fake 评测产物可读取，并检查 `.env` 不会进入 Git。
- `--full` 在默认检查通过后执行 `py -3.13 -m pytest -v` 与 `py -3.13 -m ruff check src tests app scripts`。它仍不触发真实 LLM 或破坏性数据操作。
- `--require-source-data` 额外要求 `data/raw/` 中九份 CSV 均存在，面向准备从零重建的环境。

失败信息必须说明失败层级和下一步命令。例如 Docker 不可用时提示启动 Docker Desktop；数据库不可用时提示 `docker compose up -d`；缺失 marts 时提示 `py -3.13 scripts/build_marts.py`；缺失原始 CSV 时指向 `data/README.md`；缺失模型或评测产物时提示对应训练或 fake 评测命令。脚本不泄露数据库密码、LLM Key 或完整连接串。

## 文档交付

README 使用中英双语段落，覆盖项目价值、已验证的业务发现、数据来源、快速启动、项目结构、Dashboard、机器学习、Agent 安全与评测、限制和完整复现路径。英文内容与中文内容表达相同事实，不把 fake 评测 100% 写成真实模型准确率。

`docs/data-dictionary.md` 记录 raw、staging、warehouse 与 marts 中交付相关表的粒度、主键、来源及关键字段；`docs/metric-dictionary.md` 以现有指标注册与集市 SQL 为依据定义 GMV、商品金额、订单数、客户数、延迟率、评分和 90 天复购率，并写明过滤条件和分母。

`docs/architecture.md` 使用 Mermaid 描述 CSV、分层数仓、分析集市、Dashboard、机器学习和 Agent 的单向数据流，解释金额预聚合、时间安全标签、只读 SQL 与审计轨迹。`docs/interview-guide.md` 提供中英文 3 分钟和 10 分钟项目讲述，以及至少十个技术追问与如实回答。`docs/retrospectives/final.md` 记录关键业务发现、最危险的数据错误、模型时间切分、Agent 安全边界、真实模型稳定性限制和下一轮改进建议。

## 测试与验收

新增端到端测试只检查项目交付契约：质量报告、模型文件、模型指标、Agent fake 评测文件、验证脚本和文档入口存在；它不访问 Docker、网络或真实 LLM。验证脚本自身的单元测试通过注入健康检查与命令执行器，覆盖成功、Docker 不可用、数据库不可用、缺失集市、缺失源文件、缺失产物及 `--full` 命令失败等情况。

验收命令为：

```powershell
py -3.13 scripts/verify_project.py
py -3.13 scripts/verify_project.py --full
py -3.13 -m pytest -v
py -3.13 -m ruff check src tests app scripts
```

最终交付仅在验证脚本给出成功、测试与 Ruff 通过、README 的本地启动步骤可执行且 `.env` 未追踪时完成。真实模型问数只作为可选体验，不是本地作品集的验收前提。
