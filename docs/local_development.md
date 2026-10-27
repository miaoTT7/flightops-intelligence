# 本地 PostgreSQL 开发环境

本项目使用 Docker Compose 启动一个独立的 PostgreSQL 16 服务。Compose 项目名为 `flightops-intelligence-dev`，默认只监听 `127.0.0.1:55433`，数据保存在该项目自己的 `postgres_data` 命名 volume 中。

普通的停止、启动和 `docker compose down` 不会删除数据。不要为常规操作添加 `--volumes` 或 `-v`。

## 1. 准备环境变量和 Python 环境

首次使用时：

```bash
cp .env.example .env
```

修改 `.env` 中的本地密码，并确保 `DATABASE_URL` 使用相同的用户名、密码和端口。`.env` 已被 Git 忽略。

创建 Python 虚拟环境并安装项目：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

开发依赖包含 `dbt-postgres`，因此同一个 `.venv` 同时用于 ingestion、测试和 dbt。

在每个需要运行 CLI 的新 shell 中加载变量：

```bash
set -a
source .env
set +a
```

## 2. 启动 PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

等待 `postgres` 显示为 `healthy`。也可以显式检查：

```bash
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 3. 初始化数据库 schema

该命令重复执行是安全的：

```bash
flightops-ingest init-db
```

不安装 console entry point 时可以使用：

```bash
PYTHONPATH=src python3 scripts/ingest_bts.py init-db
```

两种方式都会应用 `sql/001_phase1_ingestion.sql`。

## 4. 导入 January 2024 BTS 数据

导入整个 BTS raw 目录：

```bash
flightops-ingest ingest data/raw/bts/
```

或者只导入当前 CSV：

```bash
flightops-ingest ingest \
  'data/raw/bts/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_1/On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2024_1.csv'
```

再次执行相同命令应显示 `SKIPPED`，不会重复写入 raw 表。

## 5. 使用 SQL 检查结果

检查 raw 总行数：

```bash
docker compose exec postgres psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c 'SELECT count(*) AS raw_rows FROM raw.bts_on_time_performance;'
```

检查来源文件：

```bash
docker compose exec postgres psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c 'SELECT source_year, source_month, csv_sha256, expected_row_count FROM ingestion.source_file ORDER BY source_year, source_month;'
```

检查 ingestion batch：

```bash
docker compose exec postgres psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c 'SELECT attempt_number, status, rows_read, rows_loaded, error_type FROM ingestion.ingestion_batch ORDER BY started_at;'
```

## 6. 停止、重启与持久化

停止容器但保留容器和 volume：

```bash
docker compose stop postgres
```

重新启动：

```bash
docker compose start postgres
```

也可以移除容器和网络但保留 named volume：

```bash
docker compose down
docker compose up -d postgres
```

重启后再次执行前面的 `SELECT count(*)`，数据应保持不变。

查看本项目使用的 volume：

```bash
docker volume ls --filter label=com.flightops-intelligence.purpose=local-development
```

不要在普通开发流程中运行以下命令，因为它会请求删除 Compose volume：

```text
docker compose down --volumes
```

## 7. 运行测试

不连接数据库的测试：

```bash
pytest tests/unit tests/test_bts_profiling.py
```

如需运行数据库集成测试，建议另建专用测试数据库，不要把开发数据库传给会清理 fixture 的测试：

```bash
docker compose exec postgres createdb -U "$POSTGRES_USER" flightops_test
export TEST_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/flightops_test"
pytest tests/integration
```

集成测试仅清理它自己使用的 `2099-12` fixture 数据。

## 8. 验证 dbt 项目连接

Phase 1.3 使用现有 PostgreSQL，不启动第二个数据库。dbt 的本地 profile
位于被忽略的 `dbt/profiles.yml`，配置只引用 `.env` 中的变量。

若本地 profile 尚不存在：

```bash
cp dbt/profiles.yml.example dbt/profiles.yml
```

加载环境并验证：

```bash
source .venv/bin/activate
set -a
source .env
set +a

dbt debug --project-dir dbt --profiles-dir dbt
dbt parse --project-dir dbt --profiles-dir dbt
dbt ls --project-dir dbt --profiles-dir dbt
```

Step 1 只声明 `raw.bts_on_time_performance` source，不运行模型，也不修改
`raw` 或 `ingestion` 表。未来模型默认写入 `.env` 中 `DBT_TARGET_SCHEMA`
指定的 schema，当前示例为 `analytics`。
