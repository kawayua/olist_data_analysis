# 第 1 周学习笔记

## Day 1：可复现的开发环境

### 为什么需要虚拟环境

`.venv` 为本项目隔离 Python 依赖。项目通过 `pyproject.toml` 说明所需库，其他人不需要猜测应该安装哪些包，也不会因系统 Python 中已有的版本而得到不同结果。

### 为什么用 Docker 运行 PostgreSQL

数据库是分析项目的重要依赖。`docker-compose.yml` 把 PostgreSQL 版本、账号、数据库名、端口、持久卷和健康检查都写成可执行配置。这样开发机、演示机和未来部署环境会使用相同的数据库服务。

### 环境变量解决什么问题

`.env.example` 只提供变量名和本地开发默认值；真实的 API Key 或密码写入未提交的 `.env`。这种做法避免密钥进入 Git 历史，同时让应用可以在不同环境使用不同配置。

### 第一个测试在验证什么

`tests/test_config.py` 验证 `Settings` 会正确拼接 PostgreSQL 连接字符串。它先在 `src.config` 不存在时失败，再在最小实现后通过。这说明测试不是“事后装饰”，而是先定义我们希望配置模块提供的行为。

### 本次遇到的环境问题

Docker Desktop 重启后没有自动启动时，`docker` 客户端会提示找不到 `dockerDesktopLinuxEngine` 命名管道。确认 Docker Desktop 进程不存在后，启动 `D:\DockerDesktop\Docker Desktop.exe` 即恢复 Engine；无需重建容器或修改数据库配置。

### 本日验收命令

```powershell
.\.venv\Scripts\python -m pytest tests/test_config.py -v
.\.venv\Scripts\python -m ruff check src tests
docker compose ps
docker compose exec -T db pg_isready -U analytics -d olist
```

### 复盘问题

1. 虚拟环境和 Docker 容器分别隔离什么？
2. 为什么 `.env` 需要被 Git 忽略，但 `.env.example` 要提交？
3. 为什么不能只看 Docker Desktop 图标，而要检查 `pg_isready`？
4. 如果配置写死在代码里，部署到另一台电脑会发生什么？

## Day 2：数据契约与数据血缘

数据契约把每份 CSV 的文件名、字段顺序和主键显式写进代码。它回答的是“这份外部数据应当长什么样”，而不是“程序能否勉强读进来”。当上游文件改名、删列或改变字段拼写时，契约会在导入前发现问题。`geolocation` 没有源主键，因为同一邮编前缀在原始数据中允许出现多次；不应为了方便而强行声明一个错误主键。

## Day 3：数据库分层、事务与审计

PostgreSQL 的 Schema 是数据库内的逻辑命名空间：`raw` 保留原始事实，`staging` 做清洗，`warehouse` 建模，`marts` 提供指标，`audit` 记录运行过程。把 SQL 放入可重复执行的初始化文件，意味着新环境可以用同一命令建出相同结构。`audit.ingestion_runs` 不存业务分析结果，而是存每次导入的时间、状态、文件和行数；它让“数据从哪来、何时失败”有据可查。

## Day 4：幂等导入与数据质量

CSV 行数正确不等于数据正确：它可能少列、主键重复、订单项找不到订单，或出现不合理的负金额。导入器先校验结构，再计算 SHA-256 文件哈希；相同内容已成功导入时直接跳过。这种“重复运行不产生重复结果”的性质称为幂等性。质量报告会把行数、主键问题和业务规则异常保存为 JSON，后续每次刷新数据都可以比较变化。

### 本次真实数据发现

1. 九张 Olist 源表全部导入；最大的 `geolocation` 表有 1,000,163 行。它没有源主键是数据集的既有特性，不应把重复邮编前缀误判成错误。
2. 所有已声明主键均没有重复或空值；`order_items` 到 `orders` 的外键检查发现 0 条孤儿记录。
3. 负商品金额、负支付金额、未知订单状态，以及“交付早于下单”的记录均为 0。这些结果只说明本次规则未发现异常，不代表数据天然完美；后续仍要检查缺失、业务口径和跨表粒度。
