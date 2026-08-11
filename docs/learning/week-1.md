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
