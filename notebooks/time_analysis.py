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
    from datetime import datetime, timedelta, timezone

    import altair as alt
    import marimo as mo
    import polars as pl

    return alt, datetime, mo, pl, timedelta, timezone


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
def _(datetime, file_upload, mo, pl, timedelta, timezone):
    import json

    # JST (UTC+9) タイムゾーン
    JST = timezone(timedelta(hours=9))

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
                    dt_jst = datetime.fromtimestamp(ts / 1000, tz=JST)
                else:
                    dt_jst = datetime.fromtimestamp(ts, tz=JST)
            else:
                dt_jst = datetime.fromisoformat(str(ts))
                if dt_jst.tzinfo is None:
                    dt_jst = dt_jst.replace(tzinfo=timezone.utc).astimezone(JST)
                else:
                    dt_jst = dt_jst.astimezone(JST)

            # JSTの日時をnaive datetimeとして保存 (タイムゾーン情報を削除)
            date_jst = dt_jst.replace(tzinfo=None)

            records.append(
                {
                    "date_jst": date_jst,
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
        file_summaries = ["\n"]  # markdownレンダリングのために追加

        for file_info in file_upload.value:
            records = parse_audit_log_file(file_info)
            all_records.extend(records)
            file_summaries.append(f"- `{file_info.name}`: {len(records):,} イベント")

        df = pl.DataFrame(all_records)
        file_count = len(file_upload.value)
        files_info = "\n".join(file_summaries)
        status = mo.md(f"""
        ✅ **{len(df):,} イベントを読み込みました** ({file_count} ファイル)

        {files_info}
        """)
    else:
        status = mo.md("⏳ ファイルをアップロードしてください")
    status
    return (df,)


@app.cell
def _(df, mo):
    mo.stop(df is None, mo.md("データを読み込んでください"))


@app.cell
def _(df, mo, pl):
    # Get data range
    min_ts = df.select(pl.col("date_jst").min()).item()
    max_ts = df.select(pl.col("date_jst").max()).item()

    # Date range selector
    date_range = mo.ui.date_range(
        start=min_ts.date(),
        stop=max_ts.date(),
        label="分析対象期間",
    )
    mo.md(f"""
    ## 📅 データ期間

    - **全データ**: {min_ts.date()} 〜 {max_ts.date()} ({(max_ts - min_ts).days} 日間)
    """)
    return (date_range,)


@app.cell
def _(date_range):
    date_range


@app.cell
def _(date_range, datetime, df, mo, pl):
    # Filter by date range (date_jstはJSTのnaive datetime)
    if date_range.value:
        start_date, end_date = date_range.value
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        filtered_df = df.filter(
            (pl.col("date_jst") >= start_dt) & (pl.col("date_jst") <= end_dt)
        )
    else:
        filtered_df = df

    mo.md(f"""
    ### 📊 選択期間のデータ

    - **イベント数**: {len(filtered_df):,} / {len(df):,}
    """)
    return (filtered_df,)


@app.cell
def _(mo):
    granularity = mo.ui.dropdown(
        options=["hour", "day", "week", "month"], value="day", label="集計単位"
    )
    granularity
    return (granularity,)


@app.cell
def _(alt, filtered_df, granularity, mo, pl):
    # Aggregate by selected granularity
    if granularity.value == "hour":
        time_series = (
            filtered_df.with_columns(
                pl.col("date_jst").dt.truncate("1h").alias("period")
            )
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
            .with_columns(
                pl.col("period").dt.strftime("%Y-%m-%d %H:00").alias("period_str")
            )
        )
        x_field = "period_str:N"
        x_sort = alt.SortField("period")
    elif granularity.value == "day":
        time_series = (
            filtered_df.with_columns(pl.col("date_jst").dt.date().alias("period"))
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
            .with_columns(pl.col("period").cast(pl.Utf8).alias("period_str"))
        )
        x_field = "period_str:N"
        x_sort = alt.SortField("period")
    elif granularity.value == "week":
        time_series = (
            filtered_df.with_columns(
                pl.col("date_jst").dt.truncate("1w").alias("period")
            )
            .group_by("period")
            .agg(pl.len().alias("count"))
            .sort("period")
            .with_columns(
                pl.col("period").dt.strftime("%Y-%m-%d〜").alias("period_str")
            )
        )
        x_field = "period_str:N"
        x_sort = alt.SortField("period")
    else:  # month
        time_series = (
            filtered_df.with_columns(
                pl.col("date_jst").dt.month().alias("month"),
                pl.col("date_jst").dt.year().alias("year"),
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
                ).alias("period"),
                pl.concat_str(
                    [pl.col("year"), pl.lit("年"), pl.col("month"), pl.lit("月")]
                ).alias("period_str"),
            )
        )
        x_field = "period_str:N"
        x_sort = alt.SortField("period")

    # Create line chart
    ts_chart = (
        alt.Chart(alt.Data(values=time_series.to_dicts()))
        .mark_line(point=True)
        .encode(
            x=alt.X(x_field, title="期間", sort=x_sort),
            y=alt.Y("count:Q", title="イベント数"),
            tooltip=["period_str:N", "count:Q"],
        )
        .properties(
            title=f"アクティビティ推移（{granularity.value}別）", width=800, height=400
        )
    )

    mo.md(f"## 📊 {granularity.value}別アクティビティ")
    return (ts_chart,)


@app.cell
def _(mo, ts_chart):
    mo.ui.altair_chart(ts_chart).interactive()


@app.cell
def _(mo):
    mo.md("""
    ## ⏰ 時間帯別分布
    """)


@app.cell
def _(alt, filtered_df, mo, pl):
    # Hourly distribution
    hourly_dist = (
        filtered_df.with_columns(pl.col("date_jst").dt.hour().alias("hour"))
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
def _(alt, filtered_df, mo, pl):
    # Weekday distribution
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_dist = (
        filtered_df.with_columns(pl.col("date_jst").dt.weekday().alias("weekday"))
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
def _(filtered_df, mo, pl):
    # Off-hours analysis
    off_hours = filtered_df.filter(
        (pl.col("date_jst").dt.hour() < 9)
        | (pl.col("date_jst").dt.hour() >= 18)
        | (pl.col("date_jst").dt.weekday() >= 5)
    )

    off_hours_pct = len(off_hours) / max(len(filtered_df), 1) * 100

    mo.md(f"""
    ## 🌙 時間外アクティビティ

    - **時間外イベント数**: {len(off_hours):,}
    - **全体に占める割合**: {off_hours_pct:.1f}%

    ※ 時間外 = 9:00前、18:00以降、または週末
    """)


if __name__ == "__main__":
    app.run()
