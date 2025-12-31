# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
#     "pandas",
# ]
# ///
"""
Time Series Analysis

Analyze temporal patterns in the audit log including:
- Activity over time (hourly, daily, weekly, monthly)
- Peak activity periods
- Off-hours activity detection
"""

import marimo


__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import polars as pl

    return alt, mo, pl


@app.cell
def _(mo):
    mo.md(r"""
    # 📈 時系列分析

    このノートブックでは、Audit Logの時間的パターンを分析します。
    """)


@app.cell
def _(mo):
    file_upload = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        multiple=True,  # 複数ファイル選択を有効化
        label="Audit Logファイルをアップロード（複数選択可）",
    )
    file_upload
    return (file_upload,)


@app.cell
def _(file_upload, mo, pl):
    import json
    from datetime import datetime

    def parse_audit_log_file(file_info) -> list[dict]:
        """単一ファイルをパースしてレコードリストを返す"""
        content = file_info.contents.decode("utf-8").strip()

        if file_info.name.endswith(".ndjson") or not content.startswith("["):
            lines = [json.loads(line) for line in content.split("\n") if line.strip()]
        else:
            lines = json.loads(content)

        records = []
        for entry in lines:
            ts = entry.get("@timestamp", entry.get("timestamp"))
            if isinstance(ts, (int, float)):
                if ts > 1e12:
                    ts = datetime.fromtimestamp(ts / 1000)
                else:
                    ts = datetime.fromtimestamp(ts)
            else:
                ts = datetime.fromisoformat(str(ts))

            records.append(
                {
                    "timestamp": ts,
                    "action": entry.get("action", "unknown"),
                    "actor": entry.get("actor", "unknown"),
                    "_source_file": file_info.name,
                }
            )
        return records

    # 複数ファイルの読み込み
    df = None
    if file_upload.value:
        all_records = []
        file_summaries = []

        for file_info in file_upload.value:
            records = parse_audit_log_file(file_info)
            all_records.extend(records)
            file_summaries.append(f"- `{file_info.name}`: {len(records):,} イベント")

        df = pl.DataFrame(all_records)
        file_count = len(file_upload.value)
        files_info = "\n".join(file_summaries)
        mo.md(f"""
        ✅ **{len(df):,} イベントを読み込みました** ({file_count} ファイル)

        {files_info}
        """)
    else:
        mo.md("⏳ ファイルをアップロードしてください")
    return (df,)


@app.cell
def _(df, mo):
    mo.stop(df is None, mo.md("データを読み込んでください"))


@app.cell
def _(df, mo, pl):
    # Time range summary
    min_ts = df.select(pl.col("timestamp").min()).item()
    max_ts = df.select(pl.col("timestamp").max()).item()

    mo.md(f"""
    ## 📅 データ期間

    - **開始**: {min_ts}
    - **終了**: {max_ts}
    - **期間**: {(max_ts - min_ts).days} 日間
    """)


@app.cell
def _(mo):
    granularity = mo.ui.dropdown(
        options=["hour", "day", "week", "month"], value="day", label="集計単位"
    )
    granularity
    return (granularity,)


@app.cell
def _(alt, df, granularity, mo, pl):
    # Aggregate by selected granularity
    if granularity.value == "hour":
        time_series = (
            df.with_columns(pl.col("timestamp").dt.truncate("1h").alias("period"))
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
        )
    elif granularity.value == "day":
        time_series = (
            df.with_columns(pl.col("timestamp").dt.date().alias("period"))
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
        )
    elif granularity.value == "week":
        time_series = (
            df.with_columns(pl.col("timestamp").dt.truncate("1w").alias("period"))
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
        )
    else:  # month
        time_series = (
            df.with_columns(
                pl.col("timestamp").dt.month().alias("month"),
                pl.col("timestamp").dt.year().alias("year"),
            )
            .group_by(["year", "month"])
            .agg(pl.len().alias("count"))
            .sort(["year", "month"])
            .with_columns(
                pl.concat_str(
                    [
                        pl.col("year"),
                        pl.lit("-"),
                        pl.col("month").cast(pl.Utf8).str.zfill(2),
                    ]
                ).alias("period")
            )
        )

    # Create line chart
    ts_chart = (
        alt.Chart(alt.Data(values=time_series.to_dicts()))
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "period:T" if granularity.value != "month" else "period:N", title="期間"
            ),
            y=alt.Y("count:Q", title="イベント数"),
            tooltip=["period:N", "count:Q"],
        )
        .properties(
            title=f"アクティビティ推移（{granularity.value}別）", width=800, height=400
        )
    )

    mo.md(f"## 📊 {granularity.value}別アクティビティ")
    return (ts_chart,)


@app.cell
def _(mo, ts_chart):
    mo.ui.altair_chart(ts_chart)


@app.cell
def _(mo):
    mo.md("""
    ## ⏰ 時間帯別分布
    """)


@app.cell
def _(alt, df, mo, pl):
    # Hourly distribution
    hourly_dist = (
        df.with_columns(pl.col("timestamp").dt.hour().alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("count"))
        .sort("hour")
    )

    hourly_chart = (
        alt.Chart(alt.Data(values=hourly_dist.to_dicts()))
        .mark_bar()
        .encode(
            x=alt.X("hour:O", title="時間 (0-23)"),
            y=alt.Y("count:Q", title="イベント数"),
            color=alt.condition(
                alt.datum.hour >= 9 and alt.datum.hour < 18,
                alt.value("#4c78a8"),  # Business hours
                alt.value("#f58518"),  # Off hours
            ),
            tooltip=["hour:O", "count:Q"],
        )
        .properties(
            title="時間帯別アクティビティ（オレンジ=時間外）", width=600, height=300
        )
    )

    mo.ui.altair_chart(hourly_chart)


@app.cell
def _(mo):
    mo.md("""
    ## 📅 曜日別分布
    """)


@app.cell
def _(alt, df, mo, pl):
    # Weekday distribution
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_dist = (
        df.with_columns(pl.col("timestamp").dt.weekday().alias("weekday"))
        .group_by("weekday")
        .agg(pl.len().alias("count"))
        .sort("weekday")
        .with_columns(
            pl.col("weekday")
            .replace_strict(dict(enumerate(weekday_names)), default="不明")
            .alias("weekday_name")
        )
    )

    weekday_chart = (
        alt.Chart(alt.Data(values=weekday_dist.to_dicts()))
        .mark_bar()
        .encode(
            x=alt.X("weekday_name:N", title="曜日", sort=weekday_names),
            y=alt.Y("count:Q", title="イベント数"),
            color=alt.condition(
                alt.datum.weekday >= 5,
                alt.value("#f58518"),  # Weekend
                alt.value("#4c78a8"),  # Weekday
            ),
            tooltip=["weekday_name:N", "count:Q"],
        )
        .properties(
            title="曜日別アクティビティ（オレンジ=週末）", width=500, height=300
        )
    )

    mo.ui.altair_chart(weekday_chart)


@app.cell
def _():
    return


@app.cell
def _(df, mo, pl):
    # Off-hours analysis
    off_hours = df.filter(
        (pl.col("timestamp").dt.hour() < 9)
        | (pl.col("timestamp").dt.hour() >= 18)
        | (pl.col("timestamp").dt.weekday() >= 5)
    )

    off_hours_pct = len(off_hours) / len(df) * 100

    mo.md(f"""
    ## 🌙 時間外アクティビティ

    - **時間外イベント数**: {len(off_hours):,}
    - **全体に占める割合**: {off_hours_pct:.1f}%

    ※ 時間外 = 9:00前、18:00以降、または週末
    """)


if __name__ == "__main__":
    app.run()
