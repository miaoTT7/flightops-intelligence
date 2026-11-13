# Phase 3A Step 2：机场时区与 UTC 重建

## 来源与版本

| 来源 | 本步骤用途 | 固定版本与许可/限制 |
|---|---|---|
| [BTS TranStats 字段定义](https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) 与 Technical Directives [#31](https://www.bts.gov/sites/bts.dot.gov/files/docs/explore-topics-and-geography/topics/airlines-and-airports/224571/technical-directive-no-31-time-2019_1.pdf)、[#38](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-38-technical-directive-reporting-air)、[#39](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-39-technical-directive-reporting-time) | 当地时间、elapsed time、delay、取消、备降和 tail 语义 | 美国政府资料；BTS 不提供 IANA timezone。 |
| [FAA NASR 28-Day Subscription](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/) | 官方机场参考、坐标与历史 cycle 的候选权威来源 | FAA 公开资料；APT 数据含坐标但不应假定含 IANA timezone。本步骤没有把 NASR 当作 timezone 来源。 |
| [OurAirports](https://ourairports.com/data/) | 对机场代码、名称与坐标进行辅助交叉核对 | 2026-10-29 commit `2e34576752d971d8ce38b7187c6588e699535a29`；CSV SHA-256 `f508467c19122ea549200daa215ea477eae2dc5375f339fd4e8226736c5981ea`；Public Domain。它不提供 timezone。 |
| [OpenFlights airports.dat](https://openflights.org/data.php) | 机场代码到 IANA/Olson zone 的基础映射 | commit `e3bc6dedbcceb8b7b74248a00dcd6207254da6bd`（2019-05-13）；SHA-256 `9387cdb38df5bd664da823f8ccb69fdd9b33a1888f5b7cca09c34a3cd9ff59f9`；Open Database License。静态快照较旧，因此不是航空导航资料。 |
| [IANA Time Zone Database](https://www.iana.org/time-zones) | 2024–2025 UTC offset 与 DST 历史规则 | 固定为 tzdb `2025b`（2025-03-22）；IANA 数据为 public domain。PostgreSQL 实际安装的 zone 名称也由测试验证。 |

未使用固定 UTC offset，也未声称 FAA NASR 直接提供 IANA zone。OpenFlights 已覆盖 355 个代码；`BIH`、`EAR`、`XWA` 因缺失或 timezone 为空，依据其经核对的机场所在地分别映射为 `America/Los_Angeles`、`America/Chicago`、`America/Chicago`，并用独立 `mapping_method` 标记。未来生产化前，仍建议用固定版本 timezone-boundary-builder 对全部坐标执行第二次地理复核。

## 覆盖范围

Core 中有 516 个 `airport_sequence_id` 历史版本，对应 358 个 durable `airport_id`/机场代码。范围包括美国本土、阿拉斯加、夏威夷、波多黎各、美属维京群岛、关岛、塞班和美属萨摩亚。`ref_airport_timezones` 以 durable `airport_id` 为粒度，历史版本通过该 ID 共享映射；映射必须一对一且 IANA 名称必须被 PostgreSQL 识别。

## UTC 重建原型

`int_flight_timestamps_sample` 只抽取少量代表性记录，包括跨时区、表面跨夜、DST 切换日、取消、备降和 raw `2400` 场景。它不是全量生产表。

1. Scheduled departure 使用 `flight_date + local time + raw-2400 offset`，在 origin IANA zone 下生成默认、前一小时和后一小时候选；只有 round-trip 回当地时间后仍相同的候选有效。零候选表示 DST gap，多候选表示 DST fold，均不强行选择。
2. Scheduled arrival 对目的地当地日期生成 `-1/0/+1/+2` 候选，并仅接受与有效 `scheduled_elapsed_minutes` 在一分钟内一致的唯一 UTC 候选。
3. Actual departure 以唯一 scheduled departure UTC 加 signed departure delay 推导，再与报告的当地 actual time 交叉检查。
4. Actual arrival 以 actual departure UTC 加有效 actual elapsed minutes 推导，再与报告的当地时间及 signed arrival delay 交叉检查。
5. 取消和备降记录仍保留；不适用、缺失、无一致候选、DST 歧义及交叉检查失败均输出显式状态，不写成伪造时间。

原型不会将 actual outcome 字段作为未来 pre-departure predictor。actual timestamps 仅用于 rotation 验证和事后分析；后续 ML 特征必须另行执行 availability/leakage 审计。

## 生产化门槛

在建立全量 timestamp 模型前仍需：固定 timezone boundary 数据版本并复核全部机场；审阅所有 sample mismatch；明确容差；测试 DST fold/gap；确认全量查询性能和物化策略。只有这些门槛通过后，才应进入 aircraft rotation matching。

## January 2025 pilot

`int_flight_timestamps` 复用 `phase3a_resolve_flight_timestamps` 宏中的 sample
算法。January pilot使用 `[2025-01-01, 2025-02-01)`；当前 incremental模型要求
调用方显式提供 `phase3a_batch_start_date` 和 `phase3a_batch_end_date`，且必须恰好
覆盖一个 calendar month。模型保留范围内每个
`flight_record_key`，无法唯一解析的记录通过 status 字段保留，不静默过滤。

January pilot 的异常由 `audit_flight_timestamp_anomalies` 复现。稳定审计身份
使用 immutable CSV SHA-256 与 `source_row_number`，而不是数据库重建后可能
变化的 `flight_record_key`。审计分别量化 scheduled local clock 与
`CRSElapsedTime`、actual local clock 与 `ActualElapsedTime` 的最小差值；它只
解释和分类异常，不修正 Raw 或 Core 值。

### January anomaly baseline

January pilot 有 13 条 distinct source records：8 条 scheduled clock/elapsed
不一致、8 条 actual clock/elapsed 不一致，其中 3 条重叠。所有记录来自固定的
January 2025 CSV；回归测试使用 `csv_sha256 + source_row_number`。Scheduled
异常的最小误差范围为 2–180 分钟；actual mismatch 为 1–39 分钟。取消与备降
分别解释其中 2 条和 1 条 scheduled anomaly，但不会被改写为正常 timestamp。

## Local full-scale execution plan

January 的 539,747 行 table 为 235 MB（约 455.6 heap bytes/row），据此估计
14,080,680 行全量 heap 约 6.0 GiB。当前 `fact_flights` 为 6.2 GiB、无 index；
month predicate 使用 parallel sequential scan。一次 table replacement 会同时保留
old/new relation，并叠加 candidate aggregation、排序、测试和 WAL/temp 空间，因此在
约 25 GiB free disk 下不采用。

推荐先把 production model 改为有强制单月范围的 incremental `delete+insert`：

1. 每次只处理一个 half-open calendar month，拒绝空范围、跨月范围和无意全量。
2. 以 `flight_record_key` 为 unique key，并在写入前删除同一 `flight_date` 范围，
   使单月 rerun 幂等。
3. 每月运行 model tests、月级 input/output reconciliation、status profile和 anomaly
   audit；通过后再前进一个月。
4. 24 个月完成后运行一次全局 key uniqueness、总行数和月份覆盖测试；不要每月对
   累积 target 重跑全表 lineage join。
5. 保留至少 target projected size + 最大单月 staging + PostgreSQL temp/WAL + 安全
   余量；运行期间监控 volume free space和 `pg_stat_database.temp_bytes`。

是否添加 `(flight_date)` source index需独立决策。Raw 同类 index 当前约 90 MB，
但 Core index 的实际 build space、WAL、维护成本必须先用 staging estimate评估；
本步骤不创建 index。即使没有 index，24 次 full Core scan增加 I/O，但峰值磁盘仍
显著低于 full table replacement。

## Independent timezone mapping audit plan

使用 timezone-boundary-builder `2025b` comprehensive boundary release与项目固定的
IANA tzdb `2025b` 对齐；固定 release tag/commit、asset SHA-256与 ODbL license。
机场坐标使用固定版本 FAA NASR archived coordinates为主，固定 OurAirports snapshot
作为交叉核对：

1. 用 durable `airport_id`、IATA/FAA/ICAO code和名称建立一对一 coordinate crosswalk。
2. 对 358 个坐标执行 point-in-polygon，比较 boundary `tzid` 与
   `ref_airport_timezones.iana_timezone`，保存 matched/mismatch/no-polygon状态。
3. 对 timezone boundary一定距离内、多时区州、Arizona、Hawaii、territories及
   BIH/EAR/XWA执行人工复核；机场 reference point不等同整个机场边界。
4. 对 alias/merged zone名称同时比较 PostgreSQL/tzdb规则在 2024–2025 的 UTC offset
   序列，避免仅因等价 IANA alias产生假 mismatch。
5. 任何 mapping change必须作为显式、reviewed source update并重新运行 DST和UTC
   regression tests；本 audit 不自动改 mapping。

实际独立 audit 使用 pinned OurAirports commit和 timezone-boundary-builder 2025b：
358 个机场中 325 个 exact `tzid` match、33 个经 2024–2025逐日 UTC offset序列
证明为 alias-equivalent、0 unresolved。PBI在 coordinate snapshot中以 `ident=KPBI`
出现且 IATA字段已变化，因此 audit显式记录 `PBI -> KPBI` historical coordinate
alias；它不修改项目 airport code或 timezone mapping。

## Automated monthly workflow

全 24 月最终入口是一条命令：

```bash
.venv/bin/python scripts/run_phase3a_utc_batches.py \
  --start-month 2024-01 --end-month 2025-12 --batch-size 3 --resume
```

Runner 在 timezone audit不是 358/358、存在 unresolved mapping时拒绝真实执行。
它还拒绝非单月 dbt window和 `--full-refresh`，每月要求至少 10 GiB free space，
另加 2 GiB或根据输入行数计算出的更大 working margin。

Checkpoint 位于 `.phase3a/utc_batches_checkpoint.json`，原子写入且不进入 Git。
`--resume` 只跳过 status为 complete且数据库 row count、distinct key count和 key
signature仍匹配的月份。`running`/`failed`月份会幂等重跑；signature变化会停止。
每月完成前必须通过 row reconciliation、lineage、timezone、timestamp consistency
和 anomaly semantics tests，January还执行 stable anomaly lineage test。

### Interrupted-run recovery

1. 确认没有仍运行的 dbt process。
2. 不手工编辑 checkpoint；检查最后月份的 `status`。
3. 用原 start/end范围加 `--resume` 重启。
4. 已提交但未测试的 `running` 月份会重新执行 monthly `delete+insert`；dbt与
   PostgreSQL transaction保证失败月份不会部分破坏已完成月份。
5. Runner在每月前后比较所有 checkpoint-complete月份的 signature；任何历史月份
   变化都会立即停止。

Controlled test证实中断后可恢复，也暴露了 control connection必须使用 autocommit，
否则读取 audit view后会阻塞下一次 `CREATE VIEW`；runner已固定为 autocommit。
频繁强制重跑会产生 heap bloat：三个月 target为949 MB，高于按 January density
线性估计的约716 MB。Autovacuum可回收 tuple供表内复用但不缩小文件；正常全量流程
应使用 `--resume` 避免无意义重跑，并持续监控 relation size和free disk。
