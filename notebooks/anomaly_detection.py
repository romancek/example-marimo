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
Anomaly Detection

Detect suspicious patterns in the audit log:
- Off-hours activity
- Bulk operations
- Dangerous actions
- Unusual IP addresses
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
    # ⚠️ 異常検知

    Audit Log内の疑わしいパターンを検出します。
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
                    "actor_ip": entry.get("actor_ip"),
                    "org": entry.get("org", "unknown"),
                    "repo": entry.get("repo"),
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
        file_upload_result = f"""
        ✅ **{len(df):,} イベントを読み込みました** ({file_count} ファイル)

        {files_info}
        """
    else:
        file_upload_result = "⏳ ファイルをアップロードしてください"
    mo.md(file_upload_result)
    return (df,)


@app.cell
def _(df, mo):
    mo.stop(df is None, mo.md("データを読み込んでください"))


@app.cell
def _(df, mo, pl):
    # Get data range
    min_ts = df.select(pl.col("timestamp").min()).item()
    max_ts = df.select(pl.col("timestamp").max()).item()

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
def _(date_range, mo):
    date_range


@app.cell
def _(date_range, datetime, df, mo, pl):
    # Filter by date range
    if date_range.value:
        start_date, end_date = date_range.value
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        filtered_df = df.filter(
            (pl.col("timestamp") >= start_dt) & (pl.col("timestamp") <= end_dt)
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
    mo.md(r"""
    ## 🚨 危険なアクション

    セキュリティ上重要なアクションを検出します。
    """)


@app.cell
def _():
    # Define dangerous actions
    DANGEROUS_ACTIONS = {
        "repo.destroy",
        "repo.archived",
        "repo.change_visibility",
        "org.remove_member",
        "team.destroy",
        "hook.create",
        "hook.destroy",
        "protected_branch.destroy",
        "secret_scanning.disable",
    }

    HIGH_RISK_ACTIONS = {
        "org.add_billing_manager",
        "org.promote_member_to_owner",
        "deploy_key.create",
        "integration_installation.create",
    }
    return DANGEROUS_ACTIONS, HIGH_RISK_ACTIONS


@app.cell
def _(DANGEROUS_ACTIONS, HIGH_RISK_ACTIONS, filtered_df, mo, pl):
    # Detect dangerous actions
    dangerous_events = filtered_df.filter(
        pl.col("action").is_in(list(DANGEROUS_ACTIONS))
    ).sort("timestamp", descending=True)

    high_risk_events = filtered_df.filter(
        pl.col("action").is_in(list(HIGH_RISK_ACTIONS))
    ).sort("timestamp", descending=True)

    dangerous_summary = mo.md(f"""
    ### 検出結果

    | リスクレベル | 件数 |
    |------------|------|
    | 🔴 Critical (危険) | {len(dangerous_events)} |
    | 🟠 High (高リスク) | {len(high_risk_events)} |
    """)

    if len(dangerous_events) > 0:
        dangerous_title = mo.md("### 🔴 危険なアクション一覧")
        dangerous_table = mo.ui.table(dangerous_events, pagination=True, page_size=10)
        dangerous_result = mo.vstack(
            [dangerous_summary, dangerous_title, dangerous_table]
        )
    else:
        dangerous_message = mo.md("✅ 危険なアクションは検出されませんでした")
        dangerous_result = mo.vstack([dangerous_summary, dangerous_message])

    dangerous_result
    return dangerous_events, high_risk_events


@app.cell
def _(mo):
    mo.md(r"""
    ## 🌙 時間外アクティビティ

    営業時間外（9:00前、18:00以降、週末）のアクティビティを検出します。
    """)


@app.cell
def _(df, mo, pl):
    # Detect off-hours activity
    off_hours_events = df.filter(
        (pl.col("timestamp").dt.hour() < 9)
        | (pl.col("timestamp").dt.hour() >= 18)
        | (pl.col("timestamp").dt.weekday() >= 5)
    )

    # Group by actor
    off_hours_by_actor = (
        off_hours_events.filter(
            ~pl.col("actor").str.contains(r"\[bot\]")
        )  # Exclude bots
        .group_by("actor")
        .agg(pl.len().alias("off_hours_count"))
        .sort("off_hours_count", descending=True)
        .head(10)
    )

    mo.md(f"""
    ### 時間外アクティビティ統計

    - **時間外イベント総数**: {len(off_hours_events):,}
    - **全体に占める割合**: {len(off_hours_events) / len(df) * 100:.1f}%
    """)
    return off_hours_by_actor, off_hours_events


@app.cell
def _(alt, mo, off_hours_by_actor):
    if len(off_hours_by_actor) > 0:
        off_hours_chart = (
            alt.Chart(alt.Data(values=off_hours_by_actor.to_dicts()))
            .mark_bar()
            .encode(
                x=alt.X("off_hours_count:Q", title="時間外イベント数"),
                y=alt.Y("actor:N", sort="-x", title="ユーザー"),
                color=alt.value("#f58518"),
                tooltip=["actor:N", "off_hours_count:Q"],
            )
            .properties(
                title="時間外アクティビティが多いユーザー（Bot除外）",
                width=500,
                height=300,
            )
        )
        off_hours_result = mo.ui.altair_chart(off_hours_chart)
    else:
        off_hours_result = mo.md("時間外アクティビティは検出されませんでした")

    off_hours_result


@app.cell
def _(mo):
    mo.md(r"""
    ## 📊 大量操作の検出

    短時間での大量操作を検出します。
    """)


@app.cell
def _(mo):
    threshold_slider = mo.ui.slider(
        start=10, stop=200, step=10, value=50, label="閾値（1時間あたりのイベント数）"
    )
    threshold_slider
    return (threshold_slider,)


@app.cell
def _(df, mo, pl, threshold_slider):
    # Detect bulk operations
    bulk_ops = (
        df.with_columns(pl.col("timestamp").dt.truncate("1h").alias("hour_window"))
        .group_by(["actor", "action", "hour_window"])
        .agg(pl.len().alias("count"))
        .filter(pl.col("count") > threshold_slider.value)
        .sort("count", descending=True)
    )

    mo.md(f"""
    ### 大量操作の検出結果

    閾値: **{threshold_slider.value}件/時間**

    検出された大量操作: **{len(bulk_ops)}件**
    """)
    return (bulk_ops,)


@app.cell
def _(bulk_ops, mo):
    if len(bulk_ops) > 0:
        bulk_ops_result = mo.ui.table(bulk_ops, pagination=True, page_size=10)
    else:
        bulk_ops_result = mo.md("✅ 大量操作は検出されませんでした")

    bulk_ops_result


@app.cell
def _(mo):
    mo.md(r"""
    ## 🌐 IPアドレス分析

    複数のIPアドレスからアクセスしているユーザーを検出します。
    """)


@app.cell
def _(df, mo, pl):
    # IP analysis
    if "actor_ip" in df.columns:
        ip_analysis = (
            df.filter(pl.col("actor_ip").is_not_null())
            .group_by("actor")
            .agg(
                pl.n_unique("actor_ip").alias("unique_ips"),
                pl.col("actor_ip").unique().alias("ip_list"),
            )
            .filter(pl.col("unique_ips") > 2)
            .sort("unique_ips", descending=True)
        )

        if len(ip_analysis) > 0:
            ip_result = mo.md(f"""
            ### 複数IPからのアクセス

            3つ以上の異なるIPからアクセスしているユーザー: **{len(ip_analysis)}人**
            """)
        else:
            ip_result = mo.md("✅ 異常なIPパターンは検出されませんでした")
    else:
        ip_analysis = None
        ip_result = mo.md("⚠️ IPアドレス情報がデータに含まれていません")

    ip_result
    return (ip_analysis,)


@app.cell
def _(ip_analysis, mo):
    if ip_analysis is not None and len(ip_analysis) > 0:
        ip_table_result = mo.ui.table(
            ip_analysis.select(["actor", "unique_ips"]),
            pagination=True,
            page_size=10,
        )
    ip_table_result


@app.cell
def _(
    bulk_ops,
    dangerous_events,
    high_risk_events,
    ip_analysis,
    mo,
    off_hours_events,
):
    # Overall risk summary
    critical_count = len(dangerous_events)
    high_count = len(high_risk_events) + len(bulk_ops)
    medium_count = len(off_hours_events) // 100  # Simplified metric

    total_risk_score = critical_count * 10 + high_count * 5 + medium_count

    if total_risk_score == 0:
        risk_level = "🟢 低リスク"
        risk_color = "green"
    elif total_risk_score < 50:
        risk_level = "🟡 中リスク"
        risk_color = "yellow"
    elif total_risk_score < 100:
        risk_level = "🟠 高リスク"
        risk_color = "orange"
    else:
        risk_level = "🔴 重大リスク"
        risk_color = "red"

    mo.md(f"""
    ---

    ## 📋 リスクサマリー

    | 項目 | 値 |
    |------|-----|
    | 全体リスクレベル | **{risk_level}** |
    | リスクスコア | {total_risk_score} |
    | 危険アクション | {critical_count} |
    | 高リスクアクション | {len(high_risk_events)} |
    | 大量操作 | {len(bulk_ops)} |
    | 時間外イベント | {len(off_hours_events):,} |
    | 複数IPからのアクセス | {len(ip_analysis)} |
    """)


if __name__ == "__main__":
    app.run()
