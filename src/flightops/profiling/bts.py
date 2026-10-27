"""Profiling utilities for BTS Reporting Carrier On-Time Performance files.

The functions in this module never write to or modify the source CSV.  They
return ordinary Python dictionaries so the measurements can be tested and
rendered independently of the command-line entry point.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from flightops.common.checksums import file_sha256


CANDIDATE_KEY = [
    "FlightDate",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
]

TIME_COLUMNS = [
    "CRSDepTime",
    "DepTime",
    "WheelsOff",
    "WheelsOn",
    "CRSArrTime",
    "ArrTime",
    "FirstDepTime",
]

FOCUS_COLUMNS = [
    "Tail_Number",
    "CRSDepTime",
    "DepTime",
    "CRSArrTime",
    "ArrTime",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "ArrDelay",
    "ArrDelayMinutes",
    "ArrDel15",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]


def hhmm_to_minutes(values: pd.Series) -> pd.Series:
    """Convert BTS local HHMM values to minutes after midnight.

    ``2400`` is accepted as minute 1440. Invalid values become nullable
    ``Float64`` missing values. Keeping 2400 distinct lets callers advance the
    calendar date explicitly instead of silently turning it into 00:00.
    """

    numeric = pd.to_numeric(values, errors="coerce")
    whole_number = numeric.eq(numeric.round())
    hours = numeric.floordiv(100)
    minutes = numeric.mod(100)
    valid = whole_number & (
        ((hours.between(0, 23)) & minutes.between(0, 59)) | numeric.eq(2400)
    )
    return numeric.where(valid).map(
        lambda value: float(value // 100 * 60 + value % 100)
        if pd.notna(value)
        else pd.NA
    ).astype("Float64")


def local_datetime(dates: pd.Series, hhmm: pd.Series) -> pd.Series:
    """Combine a service date and BTS HHMM into a local naive timestamp."""

    parsed_dates = pd.to_datetime(dates, errors="coerce")
    minutes = hhmm_to_minutes(hhmm)
    return parsed_dates + pd.to_timedelta(minutes, unit="m")


def _count_invalid_hhmm(values: pd.Series) -> int:
    present = values.notna() & values.astype("string").str.strip().ne("")
    return int((present & hhmm_to_minutes(values).isna()).sum())


def assess_tail_sequences(frame: pd.DataFrame) -> dict[str, int | float]:
    """Assess whether tail-number rows can form plausible adjacent legs.

    A plausible connection is an adjacent pair for the same tail where the
    previous destination equals the next origin and scheduled ground time is
    between 0 and 24 hours. Times remain local; airport continuity means both
    timestamps use the same airport clock for this comparison.
    """

    required = {
        "Tail_Number",
        "FlightDate",
        "Origin",
        "Dest",
        "CRSDepTime",
        "CRSArrTime",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Cannot assess tail sequences; missing: {sorted(missing)}")

    legs = frame[list(required)].copy()
    legs["scheduled_departure"] = local_datetime(
        legs["FlightDate"], legs["CRSDepTime"]
    )
    legs["scheduled_arrival"] = local_datetime(
        legs["FlightDate"], legs["CRSArrTime"]
    )
    dep_minutes = hhmm_to_minutes(legs["CRSDepTime"])
    arr_minutes = hhmm_to_minutes(legs["CRSArrTime"])
    overnight = arr_minutes.lt(dep_minutes)
    legs.loc[overnight.fillna(False), "scheduled_arrival"] += pd.Timedelta(days=1)

    usable = legs[
        legs["Tail_Number"].notna()
        & legs["scheduled_departure"].notna()
        & legs["scheduled_arrival"].notna()
    ].sort_values(["Tail_Number", "scheduled_departure"], kind="stable")

    grouped = usable.groupby("Tail_Number", sort=False)
    previous_destination = grouped["Dest"].shift()
    previous_arrival = grouped["scheduled_arrival"].shift()
    has_previous = previous_arrival.notna()
    continuous_airport = has_previous & previous_destination.eq(usable["Origin"])
    ground_minutes = (
        usable["scheduled_departure"] - previous_arrival
    ).dt.total_seconds().div(60)
    plausible = continuous_airport & ground_minutes.between(0, 24 * 60)
    tail_sizes = grouped.size()

    rows_with_tail = int(frame["Tail_Number"].notna().sum())
    missing_tail = frame["Tail_Number"].isna()
    missing_tail_cancelled = None
    if "Cancelled" in frame:
        cancelled = pd.to_numeric(frame["Cancelled"], errors="coerce").eq(1)
        missing_tail_cancelled = int((missing_tail & cancelled).sum())
    return {
        "rows_with_tail": rows_with_tail,
        "rows_without_tail": int(frame["Tail_Number"].isna().sum()),
        "rows_without_tail_cancelled": missing_tail_cancelled,
        "tail_coverage_pct": round(rows_with_tail / len(frame) * 100, 4)
        if len(frame)
        else 0.0,
        "unique_tails": int(frame["Tail_Number"].nunique(dropna=True)),
        "tails_with_multiple_legs": int(tail_sizes.ge(2).sum()),
        "adjacent_same_tail_pairs": int(has_previous.sum()),
        "airport_continuous_pairs": int(continuous_airport.sum()),
        "plausible_connections_0_to_24h": int(plausible.sum()),
    }


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame:
        return {}
    counts = frame[column].value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    """Calculate BTS-specific profile statistics for an in-memory frame."""

    row_count = len(frame)
    missing_count = frame.isna().sum()
    column_profile = []
    for column in frame.columns:
        missing = int(missing_count[column])
        column_profile.append(
            {
                "column": str(column),
                "dtype": str(frame[column].dtype),
                "missing": missing,
                "missing_pct": round(missing / row_count * 100, 4)
                if row_count
                else 0.0,
                "distinct": int(frame[column].nunique(dropna=True)),
            }
        )

    key_available = all(column in frame for column in CANDIDATE_KEY)
    candidate_key_duplicates = (
        int(frame.duplicated(CANDIDATE_KEY, keep=False).sum())
        if key_available
        else None
    )

    time_quality = {
        column: {
            "present": int(frame[column].notna().sum()),
            "invalid_hhmm": _count_invalid_hhmm(frame[column]),
            "value_2400": int(pd.to_numeric(frame[column], errors="coerce").eq(2400).sum()),
        }
        for column in TIME_COLUMNS
        if column in frame
    }

    delay_summary: dict[str, dict[str, int | float | None]] = {}
    delay_columns = [
        "DepDelay",
        "DepDelayMinutes",
        "ArrDelay",
        "ArrDelayMinutes",
        "CarrierDelay",
        "WeatherDelay",
        "NASDelay",
        "SecurityDelay",
        "LateAircraftDelay",
    ]
    for column in delay_columns:
        if column not in frame:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        delay_summary[column] = {
            "present": int(numeric.notna().sum()),
            "missing": int(numeric.isna().sum()),
            "positive": int(numeric.gt(0).sum()),
            "mean": round(float(numeric.mean()), 4) if numeric.notna().any() else None,
            "median": round(float(numeric.median()), 4) if numeric.notna().any() else None,
            "max": round(float(numeric.max()), 4) if numeric.notna().any() else None,
        }

    operating = frame
    if "Cancelled" in frame and "Diverted" in frame:
        operating = frame[
            pd.to_numeric(frame["Cancelled"], errors="coerce").eq(0)
            & pd.to_numeric(frame["Diverted"], errors="coerce").eq(0)
        ]
    actual_completeness = {
        column: {
            "missing": int(operating[column].isna().sum()),
            "missing_pct": round(float(operating[column].isna().mean() * 100), 4)
            if len(operating)
            else 0.0,
        }
        for column in ["DepTime", "ArrTime", "WheelsOff", "WheelsOn"]
        if column in operating
    }

    return {
        "row_count": row_count,
        "column_count": len(frame.columns),
        "exact_duplicate_rows": int(frame.duplicated(keep=False).sum()),
        "exact_duplicate_excess": int(frame.duplicated(keep="first").sum()),
        "candidate_key": CANDIDATE_KEY,
        "candidate_key_duplicate_rows": candidate_key_duplicates,
        "column_profile": column_profile,
        "trailing_unnamed_columns": [
            str(column)
            for column in frame.columns
            if str(column).startswith("Unnamed:") and frame[column].isna().all()
        ],
        "cancelled_counts": _value_counts(frame, "Cancelled"),
        "cancellation_code_counts": _value_counts(frame, "CancellationCode"),
        "diverted_counts": _value_counts(frame, "Diverted"),
        "time_quality": time_quality,
        "actual_time_completeness_operated_nondiverted": actual_completeness,
        "delay_summary": delay_summary,
        "tail_sequences": assess_tail_sequences(frame),
    }


def profile_bts_csv(csv_path: str | Path) -> dict[str, Any]:
    """Read and profile one BTS CSV, including immutable file metadata."""

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, low_memory=False)
    profile = profile_dataframe(frame)
    profile["file"] = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }
    return profile


def _markdown_table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    header_list = list(headers)
    lines = [
        "| " + " | ".join(header_list) + " |",
        "| " + " | ".join(["---"] * len(header_list)) + " |",
    ]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown_report(profile: dict[str, Any]) -> str:
    """Render a complete, deterministic Chinese Markdown profile report."""

    file_info = profile["file"]
    tail = profile["tail_sequences"]
    column_rows = (
        (
            item["column"],
            item["dtype"],
            f'{item["missing"]:,}',
            f'{item["missing_pct"]:.4f}%',
            f'{item["distinct"]:,}',
        )
        for item in profile["column_profile"]
    )
    focus_lookup = {item["column"]: item for item in profile["column_profile"]}
    focus_rows = (
        (
            column,
            focus_lookup[column]["dtype"],
            f'{focus_lookup[column]["missing"]:,}',
            f'{focus_lookup[column]["missing_pct"]:.4f}%',
            f'{focus_lookup[column]["distinct"]:,}',
        )
        for column in FOCUS_COLUMNS
        if column in focus_lookup
    )
    time_rows = (
        (column, values["present"], values["invalid_hhmm"], values["value_2400"])
        for column, values in profile["time_quality"].items()
    )
    delay_rows = (
        (
            column,
            values["present"],
            values["missing"],
            values["positive"],
            values["mean"],
            values["median"],
            values["max"],
        )
        for column, values in profile["delay_summary"].items()
    )
    actual_rows = (
        (column, values["missing"], f'{values["missing_pct"]:.4f}%')
        for column, values in profile[
            "actual_time_completeness_operated_nondiverted"
        ].items()
    )

    unnamed = profile["trailing_unnamed_columns"]
    conclusion = (
        "支持，但需要质量过滤与边界处理。"
        if tail["plausible_connections_0_to_24h"] > 0
        else "当前样本未发现可直接连接的连续航段。"
    )
    lines = [
        "# Phase 1.1 — BTS 2024 年 1 月数据画像",
        "",
        "> 本报告由 `scripts/profile_bts_sample.py` 直接读取原始 BTS CSV 生成；脚本不会修改源文件。",
        "",
        "## 文件与总体结构",
        "",
        f'- 文件：`{Path(file_info["path"]).name}`',
        f'- 文件大小：{file_info["size_bytes"]:,} bytes（{file_info["size_bytes"] / 1024**2:.2f} MiB）',
        f'- SHA-256：`{file_info["sha256"]}`',
        f'- 记录数：{profile["row_count"]:,}',
        f'- Pandas 读取列数：{profile["column_count"]:,}',
        f'- 全空尾随列：{", ".join(unnamed) if unnamed else "无"}',
        "",
        "CSV 表头末尾存在额外分隔符，因此出现全空的 `Unnamed` 列。该列属于源文件格式现象，不是业务字段；原始文件保持不变。",
        "",
        "## 重复记录与候选键",
        "",
        f'- 参与完全重复组的行数：{profile["exact_duplicate_rows"]:,}',
        f'- 除每组首行外的完全重复行数：{profile["exact_duplicate_excess"]:,}',
        f'- 候选键：`{" + ".join(profile["candidate_key"])}`',
        f'- 候选键重复组涉及的行数：{profile["candidate_key_duplicate_rows"]:,}',
        "",
        "候选键重复不应自动删除；需要先确认是否存在计划变更、重复报送或其他业务原因。",
        "",
        "## 重点字段缺失与类型",
        "",
        _markdown_table(
            ["字段", "Pandas 类型", "缺失数", "缺失率", "非空 distinct"], focus_rows
        ),
        "",
        "## 取消与备降",
        "",
        f'- `Cancelled` 分布：{profile["cancelled_counts"]}',
        f'- `CancellationCode` 分布（含空值）：{profile["cancellation_code_counts"]}',
        f'- `Diverted` 分布：{profile["diverted_counts"]}',
        "",
        "取消或备降会造成实际到达时间、飞行时长和普通到达延误字段的合理缺失，不能把这些空值直接认定为数据错误。",
        "",
        "## 时间字段质量",
        "",
        _markdown_table(["字段", "非空", "非法 HHMM", "值为 2400"], time_rows),
        "",
        "### 未取消且未备降航班的实际时间完整性",
        "",
        _markdown_table(["字段", "缺失数", "缺失率"], actual_rows),
        "",
        "所有 HHMM 字段都是机场当地时间。`2400` 必须解释成次日 00:00；跨时区时不能直接用到达 HHMM 减去出发 HHMM。",
        "",
        "## 延误字段",
        "",
        _markdown_table(
            ["字段", "非空", "缺失", "> 0", "均值", "中位数", "最大值"], delay_rows
        ),
        "",
        "`DepDelay`/`ArrDelay` 是带符号延误，提前运行可为负数；对应的 `*DelayMinutes` 将提前运行记为 0。五类原因延误字段仅在满足 BTS 条件时填充，不能把其空值简单解释为零分钟。",
        "",
        "## 使用机尾号重建连续航班的可行性",
        "",
        f'- 有机尾号的记录：{tail["rows_with_tail"]:,}（{tail["tail_coverage_pct"]:.4f}%）',
        f'- 缺少机尾号的记录：{tail["rows_without_tail"]:,}',
        f'- 缺少机尾号且已取消的记录：{tail["rows_without_tail_cancelled"]:,}',
        f'- 唯一机尾号：{tail["unique_tails"]:,}',
        f'- 样本内至少有两个航段的机尾号：{tail["tails_with_multiple_legs"]:,}',
        f'- 同一机尾号按计划出发时间排序后的相邻航段对：{tail["adjacent_same_tail_pairs"]:,}',
        f'- 前序目的地等于后序出发地的航段对：{tail["airport_continuous_pairs"]:,}',
        f'- 同时满足机场连续、计划周转时间 0–24 小时的航段对：{tail["plausible_connections_0_to_24h"]:,}',
        "",
        f'**结论：{conclusion}** 可使用 `Tail_Number`、计划时间和机场连续性构建候选 aircraft rotations，但必须排除或单独处理缺失机尾号、取消、备降、不连续机场、月初/月末截断和跨午夜情况。这里的结果是可行性检查，不是最终的延误传播因果结论。',
        "",
        "## 全部字段画像",
        "",
        _markdown_table(
            ["字段", "Pandas 类型", "缺失数", "缺失率", "非空 distinct"], column_rows
        ),
        "",
        "## 方法与限制",
        "",
        "- 完全重复检查覆盖 CSV 中读取到的全部列，包括全空尾随列。",
        "- 连续航段检查仅使用 2024 年 1 月样本；月初的上一航段和月末的下一航段不可见。",
        "- 计划到达时间早于计划出发时间时，按跨午夜到达处理。",
        "- 连续性检查要求上一航段目的地与下一航段出发地一致；在同一机场比较当地时间，因此无需跨机场时区换算。",
        "- Pandas 类型是本次 CSV 解析结果，不等同于未来 PostgreSQL/dbt 的目标类型。",
        "",
    ]
    return "\n".join(lines)

