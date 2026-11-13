# Phase 1.6：KPI 定义与 Mart 规格

## 目的与适用范围

本文为 2024–2025 BTS Reporting Carrier On-Time Performance 数据定义可复现的业务指标。它是实现 dbt KPI marts 和 Tableau 之前的口径契约，不包含 SQL 实现。

Core 事实表粒度是“一条已摄取的 BTS source record”，不是去重后的现实航班。取消、备降、gate return 和潜在重复报告均保留。当前 `flight_count` 已由测试确认每行等于 1；mart 仍使用 `sum(flight_count)` 作为可加航班数。

## 官方依据

| 资料 | 适用性 |
|---|---|
| [14 CFR Part 234](https://www.ecfr.gov/current/title-14/chapter-II/subchapter-A/part-234) | 定义 reportable、cancelled、diverted、late 和 on-time flight，并规定 Form 234 报告内容。eCFR 是持续更新的非官方汇编；实现时以 2024–2025 当时有效规则和下列 directives 为准。 |
| [BTS Technical Reporting Directive #31 — On-Time Performance](https://www.bts.gov/sites/bts.dot.gov/files/docs/explore-topics-and-geography/topics/airlines-and-airports/224571/technical-directive-no-31-time-2019_1.pdf) | 2019-01-01 生效；#38 和 #39 明确继续引用其 on-time 报告规则。定义 flight operation、时间、取消、备降、CRS on-time 计算和原因延误。 |
| [BTS Technical Reporting Directive #38 — Reporting Carriers 2024](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-38-technical-reporting-directive-reporting-air) | 2024-01-01 生效；列出 2024 reporting carriers，并指定继续适用 #31。 |
| [BTS Technical Reporting Directive #39 — On-Time Performance 2025](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-39-technical-directive-reporting-time) | 2025-01-01 生效；更新 2025 carriers/airports，并说明其他报告规则仍沿用 #31。 |
| [BTS TranStats field definitions](https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) | 当前下载页面的字段语义；例如 signed `ArrDelay`、非负 `ArrDelayMinutes`、`ArrDel15`、取消与备降字段。 |

官方定义要点：

- `flight operation` 是某一航班在某一天的一次具体运行；Part 234 报告范围包含取消和备降记录。
- `late` 是实际到达登机口比公布到达时间晚 **15 分钟或以上**；`on-time` 是晚于计划 **不足 15 分钟**。
- Directive #31 的 CRS on-time percentage 为“准点到达的 reported operations / 该航班当月 total reported operations”。这与只在已完成航班中计算准点率的分析口径不同。
- 取消原因：A carrier、B weather、C NAS、D security。延误原因字段：carrier、weather、NAS、security、late-arriving aircraft。
- 原因延误只要求用于到达晚 15 分钟以上的航班；备降不要求原因数据。承运人还可按其声明的方法跟踪全部原因或主要原因，因此原因分钟不应被解释为所有航班或所有运行损失的完整分解。

## 全局计算政策

1. 不把 NULL 当作 0。所有平均值均保存独立的 `sum` 与非 NULL `count`。
2. signed delay 用于平均运行偏差；nonnegative delay 仅用于“延误分钟”或延误严重程度，不能混用。
3. 取消率和备降率以全部 reported operations 为分母。
4. 到达官方式准点率以全部 reported operations 为分母；同时保存“已观察到达航班准点率”，供运营比较，且必须使用不同名称。
5. departure KPI 的 eligible population 由 departure 指标是否非 NULL 决定。这样可保留已经离开登机口、随后 gate-return/cancel 的合法例外；不能简单以 `is_cancelled = false` 替代。
6. arrival operational KPI 的 eligible population 由 arrival 指标是否非 NULL 决定。取消和未到达计划目的地的备降通常自然排除；到达计划目的地的备降可合法包含。
7. 三个 elapsed-time validity flag 仅约束 duration KPI。延误 KPI不依赖 duration，但任何未来 duration 平均值只能使用 validity flag 为 `TRUE` 的值。
8. 所有 route 均指 scheduled origin → scheduled destination。

## KPI 定义

| KPI | 业务问题与公式 | Fact 字段、eligible population 与例外 | 性质与限制 |
|---|---|---|---|
| **1. Total Reported Flights** | BTS 报告了多少 flight operations？`reported_flights = sum(flight_count)`。 | 全部记录；取消和备降均包含。按月、航司、机场或 route 分组时仍以 source record 为原子。 | 官方 `flight operation` 概念；具体聚合是项目口径。不是唯一现实航班数，不能自行去重。 |
| **2. Arrival On-Time Rate** | 官方式：`official_arrival_ontime_count / reported_flights`，其中 numerator 为 `is_arrival_delayed_15_minutes = false`。运营辅助口径：同一 numerator / `arrival_observed_count`，其中 indicator 非 NULL。 | `is_arrival_delayed_15_minutes`、`flight_count`。官方式分母包含取消和备降；它们通常因无正常 arrival indicator 而不进入 numerator。运营口径仅含可观察到达表现。 | `<15` 分钟为官方定义。两种 rate 必须分别命名，禁止混在同一同比序列。 |
| **3. Departure 15-Minute Delay Rate** | 有 departure 表现的记录中，多少晚 15 分钟以上？`departure_delayed_15_count / departure_observed_count`。 | numerator：`is_departure_delayed_15_minutes = true`；denominator：该字段非 NULL。备降可包含；取消只有在 BTS 报告了实际 departure/delay 时才包含。 | 15 分钟 indicator 来自 BTS；此总体分母是项目运营口径，不是 Part 234 的 CRS consumer KPI。 |
| **4. Average Arrival Delay** | 有效 arrival observation 平均比计划晚/早多少？`sum(arrival_delay_minutes_signed) / count(non-null arrival_delay_minutes_signed)`。 | 使用 `arrival_delay_minutes_signed`。不以 0 填补取消/未到计划目的地的备降 NULL；到达计划目的地且有值的备降包含。 | 项目指标。负平均值表示总体提前。另可展示 `sum(arrival_delay_minutes)/count(non-null)`，但必须命名为 average nonnegative arrival delay。 |
| **5. Average Departure Delay** | 有效 departure observation 平均比计划晚/早多少？`sum(departure_delay_minutes_signed) / count(non-null departure_delay_minutes_signed)`。 | 使用 `departure_delay_minutes_signed`；NULL 不计入 sum 或 count。是否取消不作为先验过滤条件。 | 项目指标。signed 与 `departure_delay_minutes` 的非负版本不得互换。 |
| **6. Cancellation Rate** | 报告运行中多少被取消？`cancelled_flights / reported_flights`。 | numerator：`is_cancelled = true` 的 `flight_count`；denominator：全部 `flight_count`。保留 cancellation code A–D 的分项 count。 | 取消定义来自 14 CFR §234.2。数据不包括提前超过规则窗口从时刻表移除的 discontinued flight。 |
| **7. Diversion Rate** | 报告运行中多少被备降？`diverted_flights / reported_flights`。 | numerator：`is_diverted = true`；denominator：全部 `flight_count`。不以 arrival delay 是否存在判断 diversion。 | 备降定义来自 §234.2。未到计划目的地的备降通常缺失常规 arrival fields。 |
| **8. Delay Cause Breakdown** | 已报告的原因延误分钟由哪些类别构成？每类 `cause_minutes = sum(non-null cause field)`；份额为 `cause_minutes / sum(all five cause_minutes)`。另保存 `cause_reported_flights`。 | `carrier_delay_minutes`、`weather_delay_minutes`、`nas_delay_minutes`、`security_delay_minutes`、`late_aircraft_delay_minutes`。NULL 不作 0；备降不要求原因数据；不要用全部航班作为 cause-share 分母。 | 类别来自 BTS。份额是“已报告 cause minutes 的构成”，不是造成延误航班的概率，也不保证覆盖全部晚点或全部分钟。取消原因应单独以 `cancellation_code` 计数，不能混入 delay minutes。 |
| **9. Airline Performance** | 哪些 reporting carrier 的规模、准点、延误、取消和备降表现不同？ | 上述 additive components 按 `airline_key`、年月聚合；展示 `dot_airline_id`/reporting code。 | 分组是项目选择。承运人集合随 reporting threshold/自愿报告变化；同比必须解释 coverage 变化。 |
| **10. Airport Performance** | 从某机场出发的可靠性如何；到达某机场的表现如何？ | Origin：按 `origin_airport_key` 聚合 departure/cancel/diversion。Destination：按 `destination_airport_key` 聚合 arrival 指标。必须标记 airport role。 | 项目选择。不得把 origin departure rate 与 destination arrival rate放在同一无角色指标中；机场 sequence attributes 是时点版本。 |
| **11. Route Performance** | scheduled city-pair 的运行可靠性如何？ | 按 `origin_airport_key + destination_airport_key`；保存 reported、arrival/departure eligible、cancel/divert及 delay sums/counts。 | 项目选择。方向不同即不同 route；不使用实际 diverted endpoint 替换 scheduled destination。小样本 route 必须显示 denominator。 |
| **12. Monthly & YoY Trends** | 指标如何逐月变化、相对上年同月如何？`rate = monthly numerator / monthly denominator`；`YoY pp = current rate - prior-year rate`；count/delay 可计算绝对或百分比变化。 | 使用 `flight_date_key`/`flight_date` 聚合到 calendar month。先汇总 components，再算 rate；不得平均日/航司/route 百分比。 | 项目选择。只有 2024–2025 两年；2024 没有库内同比基期。coverage、航司组合和季节性都会影响解释。 |

## 推荐的 additive components

所有 mart 应优先储存以下可加列，并在最终 SELECT 或 Tableau 中由它们计算比例：

- `reported_flights`
- `official_arrival_ontime_flights`
- `arrival_observed_flights`
- `departure_delayed_15_flights`
- `departure_observed_flights`
- `arrival_delay_signed_minutes_sum`、`arrival_delay_observation_count`
- `departure_delay_signed_minutes_sum`、`departure_delay_observation_count`
- `cancelled_flights`、A–D cancellation counts
- `diverted_flights`
- 五类 `*_delay_minutes_sum`
- `cause_reported_flights`
- `invalid_scheduled_elapsed_count`、`invalid_actual_elapsed_count`、`invalid_diversion_elapsed_count`（质量监控，不是 KPI 分母）

派生公式必须使用 `numerator / nullif(denominator, 0)`。展示百分比时才乘 100，数据库中建议保留 0–1 ratio。

## 最小 KPI mart 设计

### `mart_monthly_overall_performance`

- **粒度：** 每个 calendar year/month 一行。
- **维度：** `year`、`month_number`，可加 `month_start_date`。
- **组件：** 上述全部 additive components。
- **用途：** 总体 KPI、月度和 YoY 趋势；作为其他 mart 的 reconciliation 基准。

### `mart_monthly_airline_performance`

- **粒度：** 每 calendar month × `airline_key` 一行。
- **维度：** date month、`airline_key`、`dot_airline_id`、reporting code。
- **组件：** 全部核心 numerator、denominator、delay sums/counts 和 cause minutes。
- **用途：** 航司对比；汇总到月份后必须与 overall mart 对账。

### `mart_monthly_origin_airport_performance`

- **粒度：** 每 calendar month × `origin_airport_key` 一行。
- **维度：** date month、origin airport key/code。
- **组件：** reported、departure observed/delayed、departure delay sum/count、cancel、divert和取消原因；可保留 arrival components，但必须明确它们代表“从该 origin 出发航班的到达表现”。
- **用途：** 出发机场运营。目的地机场 arrival dashboard 可从 route mart按 destination 汇总；在需求明确前不增加第五个 mart。

### `mart_monthly_route_performance`

- **粒度：** 每 calendar month × `origin_airport_key` × `destination_airport_key` 一行。
- **维度：** date month、origin/destination role-playing keys/codes。
- **组件：** reported、arrival/departure eligible与指标、delay sums/counts、cancel、divert、cause minutes。
- **用途：** 有方向的 scheduled route 分析；也支持按 destination 汇总 arrival performance。

## 数据质量与 reconciliation 测试

每个 mart 至少应验证：

1. grain 组合唯一且非 NULL；维度 key relationships 成立。
2. 所有 count/minute components 非负（signed delay sums 除外）。
3. numerator 不超过对应 denominator；`cancelled_flights`、`diverted_flights` 不超过 `reported_flights`。
4. `arrival_observed_flights <= reported_flights`、`departure_observed_flights <= reported_flights`。
5. cancellation A–D counts 之和等于 `cancelled_flights`；依赖当前 Core cancellation consistency test。
6. overall 每月 `reported_flights` 与 `fact_flights` 每月 `sum(flight_count)` 一致。
7. airline、origin airport、route mart按月汇总均与 overall additive components 对账；这同时检测漏行或 fan-out。
8. rate 只从 additive components 重算，不存储或平均下层百分比。
9. NULL delay observation 不进入 delay sum/count；已知 source anomalies 继续由现有精确例外测试管理。
10. cause minutes 仅解释为 reported cause data；测试不得强迫每条 late flight 都有每类原因值。

## 已核对的 Core 字段

上述定义引用的字段均存在于当前 `fact_flights`：`flight_record_key`、日期与四个 dimension keys、航司/机场代码、`flight_count`、signed/nonnegative departure/arrival delay、两个 15-minute indicators、cancel/divert indicators、`cancellation_code`、五类 cause minutes、三个 elapsed validity flags。当前 Core 不含机场时区、实际 diverted endpoint 维度或乘客量，因此本阶段不定义 UTC punctuality、diverted destination KPI 或 passenger-weighted KPI。

## 实现前待确认问题

1. Tableau 主卡片是否采用官方式 arrival on-time rate，还是把 completed/observed rate 作为主展示？建议两者都保留，但主卡片明确标注 denominator。
2. Airport 首页默认角色是 origin，还是提供 origin/destination 切换？当前最小 mart 以 origin 为主，destination 可从 route mart汇总。
3. Average delay 主展示是否采用 signed 平均值？本文建议 signed 为主，并将 nonnegative 平均值明确命名为 delay-only severity 辅助指标。
4. 是否设置 route/airline 最小样本展示阈值？该阈值只影响 BI 展示，不应过滤 mart 数据。
5. YoY 是否展示 percentage change 还是 percentage-point change？rate 应优先展示百分点变化，count/minutes 才使用百分比变化。

在上述展示选择确认前，可以实现 additive mart components 和测试；不能把尚未确认的展示选择硬编码成唯一业务事实。

## Step 2 实现映射

四个 mart 已按上述 grain 实现于 `dbt/models/marts/kpi/`，继承 `table` materialization 和 `analytics_marts` schema。共享的 ephemeral `int_flight_kpi_components` 只在编译 SQL 中展开，不创建额外数据库 relation；它集中定义 eligible counts、signed delay observations、取消/备降、cause data 和 elapsed anomaly counts。`kpi_metric_columns.sql` 集中定义 additive aggregation、安全除法、平均值和 cause-minute shares，避免各 mart 口径漂移。

测试覆盖 mart grain、维度关系、numerator/denominator、零分母 NULL、rate 范围、overall-to-fact reconciliation，以及 airline/origin-airport/route 到 overall 的逐月 additive reconciliation。实际构建结果记录在本阶段执行报告中，不在规格文档中固化易过期的运行数字。
