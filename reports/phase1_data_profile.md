# Phase 1.1 — BTS 2024 年 1 月数据画像

> 本报告由 `scripts/profile_bts_sample.py` 直接读取原始 BTS CSV 生成；脚本不会修改源文件。

## 文件与总体结构

- 文件：`On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2024_1.csv`
- 文件大小：246,830,488 bytes（235.40 MiB）
- SHA-256：`e92febedf6cd51bd87eca0be2fba3f5c1f383b1da41119db7f1cc1a26c4d3286`
- 记录数：547,271
- Pandas 读取列数：110
- 全空尾随列：Unnamed: 109

CSV 表头末尾存在额外分隔符，因此出现全空的 `Unnamed` 列。该列属于源文件格式现象，不是业务字段；原始文件保持不变。

## 重复记录与候选键

- 参与完全重复组的行数：0
- 除每组首行外的完全重复行数：0
- 候选键：`FlightDate + Reporting_Airline + Flight_Number_Reporting_Airline + Origin + Dest + CRSDepTime`
- 候选键重复组涉及的行数：0

候选键重复不应自动删除；需要先确认是否存在计划变更、重复报送或其他业务原因。

## 重点字段缺失与类型

| 字段 | Pandas 类型 | 缺失数 | 缺失率 | 非空 distinct |
| --- | --- | --- | --- | --- |
| Tail_Number | str | 5,293 | 0.9672% | 5,604 |
| CRSDepTime | int64 | 0 | 0.0000% | 1,239 |
| DepTime | float64 | 19,784 | 3.6150% | 1,424 |
| CRSArrTime | int64 | 0 | 0.0000% | 1,345 |
| ArrTime | float64 | 20,633 | 3.7702% | 1,440 |
| DepDelay | float64 | 19,858 | 3.6285% | 1,241 |
| DepDelayMinutes | float64 | 19,858 | 3.6285% | 1,198 |
| DepDel15 | float64 | 19,858 | 3.6285% | 2 |
| ArrDelay | float64 | 21,901 | 4.0019% | 1,282 |
| ArrDelayMinutes | float64 | 21,901 | 4.0019% | 1,198 |
| ArrDel15 | float64 | 21,901 | 4.0019% | 2 |
| Cancelled | float64 | 0 | 0.0000% | 2 |
| CancellationCode | str | 526,882 | 96.2744% | 3 |
| Diverted | float64 | 0 | 0.0000% | 2 |
| CarrierDelay | float64 | 420,861 | 76.9018% | 924 |
| WeatherDelay | float64 | 420,861 | 76.9018% | 709 |
| NASDelay | float64 | 420,861 | 76.9018% | 376 |
| SecurityDelay | float64 | 420,861 | 76.9018% | 95 |
| LateAircraftDelay | float64 | 420,861 | 76.9018% | 715 |

## 取消与备降

- `Cancelled` 分布：{'0.0': 526882, '1.0': 20389}
- `CancellationCode` 分布（含空值）：{'nan': 526882, 'B': 12085, 'A': 7736, 'C': 568}
- `Diverted` 分布：{'0.0': 545759, '1.0': 1512}

取消或备降会造成实际到达时间、飞行时长和普通到达延误字段的合理缺失，不能把这些空值直接认定为数据错误。

## 时间字段质量

| 字段 | 非空 | 非法 HHMM | 值为 2400 |
| --- | --- | --- | --- |
| CRSDepTime | 547271 | 0 | 0 |
| DepTime | 527487 | 0 | 40 |
| WheelsOff | 527014 | 0 | 58 |
| WheelsOn | 526637 | 0 | 201 |
| CRSArrTime | 547271 | 0 | 0 |
| ArrTime | 526638 | 0 | 239 |
| FirstDepTime | 4728 | 0 | 0 |

### 未取消且未备降航班的实际时间完整性

| 字段 | 缺失数 | 缺失率 |
| --- | --- | --- |
| DepTime | 0 | 0.0000% |
| ArrTime | 0 | 0.0000% |
| WheelsOff | 0 | 0.0000% |
| WheelsOn | 0 | 0.0000% |

所有 HHMM 字段都是机场当地时间。`2400` 必须解释成次日 00:00；跨时区时不能直接用到达 HHMM 减去出发 HHMM。

## 延误字段

| 字段 | 非空 | 缺失 | > 0 | 均值 | 中位数 | 最大值 |
| --- | --- | --- | --- | --- | --- | --- |
| DepDelay | 527413 | 19858 | 211862 | 15.7007 | -2.0 | 3125.0 |
| DepDelayMinutes | 527413 | 19858 | 211862 | 18.8195 | 0.0 | 3125.0 |
| ArrDelay | 525370 | 21901 | 209400 | 10.3523 | -5.0 | 3136.0 |
| ArrDelayMinutes | 525370 | 21901 | 209400 | 19.2004 | 0.0 | 3136.0 |
| CarrierDelay | 126410 | 420861 | 66482 | 24.6137 | 2.0 | 2972.0 |
| WeatherDelay | 126410 | 420861 | 12282 | 7.7475 | 0.0 | 1804.0 |
| NASDelay | 126410 | 420861 | 66322 | 13.525 | 1.0 | 1431.0 |
| SecurityDelay | 126410 | 420861 | 864 | 0.1789 | 0.0 | 1005.0 |
| LateAircraftDelay | 126410 | 420861 | 63485 | 29.3931 | 1.0 | 1565.0 |

`DepDelay`/`ArrDelay` 是带符号延误，提前运行可为负数；对应的 `*DelayMinutes` 将提前运行记为 0。五类原因延误字段仅在满足 BTS 条件时填充，不能把其空值简单解释为零分钟。

## 使用机尾号重建连续航班的可行性

- 有机尾号的记录：541,978（99.0328%）
- 缺少机尾号的记录：5,293
- 缺少机尾号且已取消的记录：5,293
- 唯一机尾号：5,604
- 样本内至少有两个航段的机尾号：5,583
- 同一机尾号按计划出发时间排序后的相邻航段对：536,374
- 前序目的地等于后序出发地的航段对：515,711
- 同时满足机场连续、计划周转时间 0–24 小时的航段对：500,969

**结论：支持，但需要质量过滤与边界处理。** 可使用 `Tail_Number`、计划时间和机场连续性构建候选 aircraft rotations，但必须排除或单独处理缺失机尾号、取消、备降、不连续机场、月初/月末截断和跨午夜情况。这里的结果是可行性检查，不是最终的延误传播因果结论。

## 全部字段画像

| 字段 | Pandas 类型 | 缺失数 | 缺失率 | 非空 distinct |
| --- | --- | --- | --- | --- |
| Year | int64 | 0 | 0.0000% | 1 |
| Quarter | int64 | 0 | 0.0000% | 1 |
| Month | int64 | 0 | 0.0000% | 1 |
| DayofMonth | int64 | 0 | 0.0000% | 31 |
| DayOfWeek | int64 | 0 | 0.0000% | 7 |
| FlightDate | str | 0 | 0.0000% | 31 |
| Reporting_Airline | str | 0 | 0.0000% | 15 |
| DOT_ID_Reporting_Airline | int64 | 0 | 0.0000% | 15 |
| IATA_CODE_Reporting_Airline | str | 0 | 0.0000% | 15 |
| Tail_Number | str | 5,293 | 0.9672% | 5,604 |
| Flight_Number_Reporting_Airline | int64 | 0 | 0.0000% | 5,914 |
| OriginAirportID | int64 | 0 | 0.0000% | 334 |
| OriginAirportSeqID | int64 | 0 | 0.0000% | 334 |
| OriginCityMarketID | int64 | 0 | 0.0000% | 311 |
| Origin | str | 0 | 0.0000% | 334 |
| OriginCityName | str | 0 | 0.0000% | 328 |
| OriginState | str | 0 | 0.0000% | 52 |
| OriginStateFips | int64 | 0 | 0.0000% | 52 |
| OriginStateName | str | 0 | 0.0000% | 52 |
| OriginWac | int64 | 0 | 0.0000% | 52 |
| DestAirportID | int64 | 0 | 0.0000% | 334 |
| DestAirportSeqID | int64 | 0 | 0.0000% | 334 |
| DestCityMarketID | int64 | 0 | 0.0000% | 311 |
| Dest | str | 0 | 0.0000% | 334 |
| DestCityName | str | 0 | 0.0000% | 328 |
| DestState | str | 0 | 0.0000% | 52 |
| DestStateFips | int64 | 0 | 0.0000% | 52 |
| DestStateName | str | 0 | 0.0000% | 52 |
| DestWac | int64 | 0 | 0.0000% | 52 |
| CRSDepTime | int64 | 0 | 0.0000% | 1,239 |
| DepTime | float64 | 19,784 | 3.6150% | 1,424 |
| DepDelay | float64 | 19,858 | 3.6285% | 1,241 |
| DepDelayMinutes | float64 | 19,858 | 3.6285% | 1,198 |
| DepDel15 | float64 | 19,858 | 3.6285% | 2 |
| DepartureDelayGroups | float64 | 19,858 | 3.6285% | 15 |
| DepTimeBlk | str | 0 | 0.0000% | 19 |
| TaxiOut | float64 | 20,257 | 3.7015% | 176 |
| WheelsOff | float64 | 20,257 | 3.7015% | 1,418 |
| WheelsOn | float64 | 20,634 | 3.7703% | 1,440 |
| TaxiIn | float64 | 20,634 | 3.7703% | 178 |
| CRSArrTime | int64 | 0 | 0.0000% | 1,345 |
| ArrTime | float64 | 20,633 | 3.7702% | 1,440 |
| ArrDelay | float64 | 21,901 | 4.0019% | 1,282 |
| ArrDelayMinutes | float64 | 21,901 | 4.0019% | 1,198 |
| ArrDel15 | float64 | 21,901 | 4.0019% | 2 |
| ArrivalDelayGroups | float64 | 21,901 | 4.0019% | 15 |
| ArrTimeBlk | str | 0 | 0.0000% | 19 |
| Cancelled | float64 | 0 | 0.0000% | 2 |
| CancellationCode | str | 526,882 | 96.2744% | 3 |
| Diverted | float64 | 0 | 0.0000% | 2 |
| CRSElapsedTime | float64 | 0 | 0.0000% | 445 |
| ActualElapsedTime | float64 | 21,901 | 4.0019% | 680 |
| AirTime | float64 | 21,901 | 4.0019% | 638 |
| Flights | float64 | 0 | 0.0000% | 1 |
| Distance | float64 | 0 | 0.0000% | 1,483 |
| DistanceGroup | int64 | 0 | 0.0000% | 11 |
| CarrierDelay | float64 | 420,861 | 76.9018% | 924 |
| WeatherDelay | float64 | 420,861 | 76.9018% | 709 |
| NASDelay | float64 | 420,861 | 76.9018% | 376 |
| SecurityDelay | float64 | 420,861 | 76.9018% | 95 |
| LateAircraftDelay | float64 | 420,861 | 76.9018% | 715 |
| FirstDepTime | float64 | 542,543 | 99.1361% | 1,134 |
| TotalAddGTime | float64 | 542,543 | 99.1361% | 221 |
| LongestAddGTime | float64 | 542,543 | 99.1361% | 209 |
| DivAirportLandings | int64 | 0 | 0.0000% | 5 |
| DivReachedDest | float64 | 545,759 | 99.7237% | 2 |
| DivActualElapsedTime | float64 | 546,003 | 99.7683% | 612 |
| DivArrDelay | float64 | 546,003 | 99.7683% | 563 |
| DivDistance | float64 | 545,759 | 99.7237% | 135 |
| Div1Airport | str | 545,627 | 99.6996% | 169 |
| Div1AirportID | float64 | 545,627 | 99.6996% | 169 |
| Div1AirportSeqID | float64 | 545,627 | 99.6996% | 169 |
| Div1WheelsOn | float64 | 545,627 | 99.6996% | 866 |
| Div1TotalGTime | float64 | 545,627 | 99.6996% | 159 |
| Div1LongestGTime | float64 | 545,627 | 99.6996% | 143 |
| Div1WheelsOff | float64 | 545,985 | 99.7650% | 754 |
| Div1TailNum | str | 545,985 | 99.7650% | 1,082 |
| Div2Airport | str | 547,233 | 99.9931% | 20 |
| Div2AirportID | float64 | 547,233 | 99.9931% | 20 |
| Div2AirportSeqID | float64 | 547,233 | 99.9931% | 20 |
| Div2WheelsOn | float64 | 547,233 | 99.9931% | 37 |
| Div2TotalGTime | float64 | 547,233 | 99.9931% | 28 |
| Div2LongestGTime | float64 | 547,233 | 99.9931% | 28 |
| Div2WheelsOff | float64 | 547,250 | 99.9962% | 21 |
| Div2TailNum | str | 547,250 | 99.9962% | 21 |
| Div3Airport | str | 547,270 | 99.9998% | 1 |
| Div3AirportID | float64 | 547,270 | 99.9998% | 1 |
| Div3AirportSeqID | float64 | 547,270 | 99.9998% | 1 |
| Div3WheelsOn | float64 | 547,270 | 99.9998% | 1 |
| Div3TotalGTime | float64 | 547,270 | 99.9998% | 1 |
| Div3LongestGTime | float64 | 547,270 | 99.9998% | 1 |
| Div3WheelsOff | float64 | 547,270 | 99.9998% | 1 |
| Div3TailNum | str | 547,270 | 99.9998% | 1 |
| Div4Airport | float64 | 547,271 | 100.0000% | 0 |
| Div4AirportID | float64 | 547,271 | 100.0000% | 0 |
| Div4AirportSeqID | float64 | 547,271 | 100.0000% | 0 |
| Div4WheelsOn | float64 | 547,271 | 100.0000% | 0 |
| Div4TotalGTime | float64 | 547,271 | 100.0000% | 0 |
| Div4LongestGTime | float64 | 547,271 | 100.0000% | 0 |
| Div4WheelsOff | float64 | 547,271 | 100.0000% | 0 |
| Div4TailNum | float64 | 547,271 | 100.0000% | 0 |
| Div5Airport | float64 | 547,271 | 100.0000% | 0 |
| Div5AirportID | float64 | 547,271 | 100.0000% | 0 |
| Div5AirportSeqID | float64 | 547,271 | 100.0000% | 0 |
| Div5WheelsOn | float64 | 547,271 | 100.0000% | 0 |
| Div5TotalGTime | float64 | 547,271 | 100.0000% | 0 |
| Div5LongestGTime | float64 | 547,271 | 100.0000% | 0 |
| Div5WheelsOff | float64 | 547,271 | 100.0000% | 0 |
| Div5TailNum | float64 | 547,271 | 100.0000% | 0 |
| Unnamed: 109 | float64 | 547,271 | 100.0000% | 0 |

## 方法与限制

- 完全重复检查覆盖 CSV 中读取到的全部列，包括全空尾随列。
- 连续航段检查仅使用 2024 年 1 月样本；月初的上一航段和月末的下一航段不可见。
- 计划到达时间早于计划出发时间时，按跨午夜到达处理。
- 连续性检查要求上一航段目的地与下一航段出发地一致；在同一机场比较当地时间，因此无需跨机场时区换算。
- Pandas 类型是本次 CSV 解析结果，不等同于未来 PostgreSQL/dbt 的目标类型。
