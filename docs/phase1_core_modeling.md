# Phase 1.4 — Core 数据模型约定

## 分层与数据库 schema

数据流保持为：

```text
Raw → Staging → Core → KPI Marts
```

- **Raw**：Python 摄取拥有的不可变 BTS 源记录，位于 `raw`。
- **Staging**：一行对应一条源记录，负责重命名、类型转换和源数据质量验证；当前模型位于 `analytics_staging`。
- **Core**：共享的维度和最细粒度事实模型。代码放在 dbt 的 `models/marts/core/`，作为面向下游消费者的 marts 模型；marts 路径配置为 table，并使用 custom schema `marts`。在默认 target schema `analytics` 下，实际位于 `analytics_marts`。
- **KPI Marts**：以后基于 Core 构建业务口径明确的聚合模型；本步骤不实现。

项目使用 dbt 默认 schema 生成规则，即 `<target_schema>_<custom_schema>`，不覆盖 `generate_schema_name`。

## 计划中的 Core 模型

| 模型 | 目的与粒度 |
|---|---|
| `fact_flights` | 航班运行事实；一行严格对应一条 `stg_bts_flights` 源记录，包括取消、备降和可能重复报告的记录。 |
| `dim_airlines` | 航司共享维度；初始粒度为一个 `dot_airline_id`。 |
| `dim_airports` | 机场共享维度；粒度为一个 `airport_sequence_id`，由事实表以始发和目的机场两种角色引用。 |
| `dim_dates` | 日历维度；一行对应一个自然日。 |

不因目录存在而创建占位模型；每个模型将在后续步骤分别实现和验证。

## 键与记录身份

- Core 主键采用确定性仓库键；同时保留对应的 BTS 自然键。
- `fact_flights.flight_record_key` 沿用 staging 的技术源行键。它标识当前摄取 lineage 中的 CSV 记录，不是现实世界唯一航班号，也不保证在独立重建的数据库之间不变。
- 事实表计划通过 `airline_key`、`origin_airport_key`、`destination_airport_key` 和 `flight_date_key` 引用共享维度。
- 航班日期、航司代码、航班号、机场和计划时间的组合不得被假定为唯一业务键，也不得用于静默去重。

## 历史属性和冲突处理

- `dot_airline_id` 是初始航司自然键；`reporting_airline_code` 和 IATA code 是描述属性。构建维度前必须检测同一 DOT ID 的属性冲突。
- `airport_id` 表示跨时期的机场身份；`airport_sequence_id` 表示 BTS 提供的时点属性版本。构建维度前必须检测同一 sequence ID 的属性冲突。
- 不得用 `MIN()`、`MAX()`、无确定顺序的去重或任意取值掩盖冲突。冲突应使质量测试失败并触发调查。
- 当前不预先实现 SCD Type 2；只有多月份数据证明存在需要保留的历史变化时再引入。

## 完整性要求

`fact_flights` 必须保留 staging 的全部记录和 lineage，不过滤或合并取消、备降、gate-return 或疑似重复记录。实现时至少验证：

- fact 与 staging 总行数一致；
- `flight_record_key` 唯一且非空，并在两层间双向无遗漏；
- 每个 staging 行最多匹配一个维度版本，维度连接不产生 fan-out；
- 取消和备降记录数量在转换前后一致；
- 所有非空维度键通过 relationship tests。

## 测试与数据库约束

dbt 的 `unique`、`not_null` 和 `relationships` data tests 是构建后运行的查询，用于发现当前数据中的违规行；它们不会在 PostgreSQL 中创建或持续强制执行 `PRIMARY KEY`、`UNIQUE` 或 `FOREIGN KEY` constraint。

Core 初始实现以 dbt tests 和受控构建验证逻辑完整性。是否增加 PostgreSQL 物理约束属于后续独立决策，不应在文档中把 dbt test 表述为数据库约束。
