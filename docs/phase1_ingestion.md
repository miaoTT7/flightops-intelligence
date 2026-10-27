# Phase 1.2 — BTS 多月份摄取

该摄取器接受 BTS CSV、包含单个 CSV 的 ZIP，或递归目录。原始文件不会被移动、修改或删除。CSV 内容以解压后的 SHA-256 标识，因此同一数据同时以 ZIP 和 CSV 出现时只会加载一次。

本地 PostgreSQL 16 的完整启动、持久化和验证步骤见 [`docs/local_development.md`](local_development.md)。

## 数据库初始化

安装项目及开发依赖：

```bash
python -m pip install -e '.[dev]'
```

设置 PostgreSQL 连接并创建表：

```bash
export DATABASE_URL='postgresql://user:password@localhost:5432/flightops'
flightops-ingest init-db
```

数据库包含：

- `ingestion.source_file`：CSV 内容身份、月份、schema fingerprint 和期望行数。
- `ingestion.ingestion_batch`：每次成功、失败或跳过的尝试。
- `raw.bts_on_time_performance`：109 个 BTS 原始字段，均以文本保留，并附带文件、batch 和源行号。

## 摄取

处理一个文件或整个目录：

```bash
flightops-ingest ingest data/raw/bts/month.zip
flightops-ingest ingest data/raw/bts/
```

也可不安装命令行入口：

```bash
PYTHONPATH=src python scripts/ingest_bts.py --dsn "$DATABASE_URL" ingest data/raw/bts/
```

摄取前会流式检查 ZIP、CSV schema、行宽以及整文件年月。成功加载使用 PostgreSQL `COPY`。raw 插入和 batch 的 `succeeded` 更新处于同一事务；任一步失败都会回滚 raw 数据，再用独立事务记录 `failed`。

已成功的相同 CSV SHA-256 会记录为 `skipped`，不会重复加载。相同月份若出现不同 SHA-256，当前版本会以 `SOURCE_PERIOD_CONFLICT` 拒绝，避免无审计的历史覆盖。

## 测试

单元测试不需要 PostgreSQL：

```bash
pytest tests/unit tests/test_bts_profiling.py
```

集成测试只会在显式设置专用测试数据库时运行：

```bash
export TEST_DATABASE_URL='postgresql://user:password@localhost:5432/flightops_test'
pytest tests/integration
```

集成测试会创建项目 schema，并只清理其自身使用的 `2099-12` fixture 数据。不要把 `TEST_DATABASE_URL` 指向生产数据库。

## 当前边界

- 不自动下载 BTS 数据。
- 不自动替换同月份的修订文件。
- raw 层不做业务类型转换；类型转换属于后续 dbt staging 工作。
- 进程被操作系统强制终止时，已提交的 `running` batch 可能需要人工检查；raw 数据事务仍会由 PostgreSQL 回滚。
