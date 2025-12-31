# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
#     "pydantic",
#     "pandas",
# ]
# ///
"""
User Activity Analysis

Analyze per-user patterns in the audit log including:
- Activity counts and distributions
- Most active users
- Action type breakdown per user
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
    # 👥 ユーザー別アクティビティ分析

    このノートブックでは、Audit Logをユーザー別に分析します。
    """)


@app.cell
def _(mo):
    # File upload widget
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
    # User activity summary
    user_counts = (
        df.group_by("actor")
        .agg(pl.len().alias("event_count"))
        .sort("event_count", descending=True)
    )

    mo.md(f"""
    ## 📊 サマリー

    - **総ユーザー数**: {user_counts.height}
    - **総イベント数**: {df.height}
    - **平均イベント/ユーザー**: {df.height / user_counts.height:.1f}
    """)


@app.cell
def _(mo):
    # Controls
    top_n_slider = mo.ui.slider(
        start=5, stop=50, step=5, value=10, label="表示するユーザー数"
    )
    exclude_bots = mo.ui.checkbox(value=True, label="Botを除外")
    mo.hstack([top_n_slider, exclude_bots])
    return exclude_bots, top_n_slider


@app.cell
def _(alt, df, exclude_bots, mo, pl, top_n_slider):
    # Filter bots if needed
    filtered_df = df
    if exclude_bots.value:
        filtered_df = df.filter(~pl.col("actor").str.contains(r"\[bot\]"))

    # Get top users
    top_users = (
        filtered_df.group_by("actor")
        .agg(pl.len().alias("event_count"))
        .sort("event_count", descending=True)
        .head(top_n_slider.value)
    )

    # Create chart
    chart = (
        alt.Chart(top_users.to_dicts())
        .mark_bar()
        .encode(
            x=alt.X("event_count:Q", title="イベント数"),
            y=alt.Y("actor:N", sort="-x", title="ユーザー"),
            color=alt.Color("event_count:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["actor:N", "event_count:Q"],
        )
        .properties(
            title=f"Top {top_n_slider.value} アクティブユーザー", width=600, height=400
        )
    )

    mo.md(f"## 🏆 最もアクティブなユーザー Top {top_n_slider.value}")
    return chart, filtered_df, top_users


@app.cell
def _(chart, mo):
    mo.ui.altair_chart(chart)


@app.cell
def _(filtered_df, mo, pl):
    # Action breakdown per user
    action_breakdown = (
        filtered_df.group_by(["actor", "action"])
        .agg(pl.len().alias("count"))
        .sort(["actor", "count"], descending=[False, True])
    )

    mo.md("## 📋 ユーザー別アクション内訳")
    return (action_breakdown,)


@app.cell
def _(mo, top_users):
    # User selector
    user_selector = mo.ui.dropdown(
        options=top_users["actor"].to_list(), label="ユーザーを選択"
    )
    user_selector
    return (user_selector,)


@app.cell
def _(action_breakdown, alt, mo, pl, user_selector):
    print(user_selector.value)
    if user_selector.value:
        user_actions = action_breakdown.filter(pl.col("actor") == user_selector.value)

        action_chart = (
            alt.Chart(user_actions.to_dicts())
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="回数"),
                y=alt.Y("action:N", sort="-x", title="アクション"),
                color=alt.Color("action:N", legend=None),
                tooltip=["action:N", "count:Q"],
            )
            .properties(
                title=f"{user_selector.value} のアクション内訳", width=600, height=300
            )
        )

        mo.ui.altair_chart(action_chart)
    else:
        mo.md("ユーザーを選択してください")
    return (action_chart,)


@app.cell
def _(action_chart, mo):
    mo.ui.altair_chart(action_chart)


if __name__ == "__main__":
    app.run()
