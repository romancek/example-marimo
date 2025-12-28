# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
# ]
# ///
"""
Action Tracker

Track and filter specific actions in the audit log:
- Filter by action type
- Search specific events
- Repository/team-level aggregation
"""

import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import altair as alt
    return alt, mo, pl


@app.cell
def _(mo):
    mo.md(
        r"""
        # 🔎 アクション追跡

        特定のアクションを追跡・フィルタリングします。
        """
    )
    return


@app.cell
def _(mo):
    file_upload = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        multiple=False,
        label="Audit Logファイルをアップロード"
    )
    file_upload
    return (file_upload,)


@app.cell
def _(file_upload, mo, pl):
    import json
    from datetime import datetime

    df = None
    if file_upload.value:
        file_info = file_upload.value[0]
        content = file_info.contents.decode("utf-8")

        if file_info.name.endswith(".ndjson"):
            lines = [json.loads(line) for line in content.strip().split("\n") if line]
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
                ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))

            records.append({
                "timestamp": ts,
                "action": entry.get("action", "unknown"),
                "actor": entry.get("actor", "unknown"),
                "org": entry.get("org", "unknown"),
                "repo": entry.get("repo"),
                "user": entry.get("user"),
                "team": entry.get("team"),
            })

        df = pl.DataFrame(records)
        mo.md(f"✅ {len(df)} イベントを読み込みました")
    else:
        mo.md("⏳ ファイルをアップロードしてください")
    return content, datetime, df, file_info, json, lines, records, ts


@app.cell
def _(df, mo):
    mo.stop(df is None, mo.md("データを読み込んでください"))
    return


@app.cell
def _(df, mo, pl):
    # Get unique actions
    unique_actions = df.select(pl.col("action").unique()).sort("action")["action"].to_list()

    mo.md(f"## 📋 アクション一覧 ({len(unique_actions)} 種類)")
    return (unique_actions,)


@app.cell
def _(mo, unique_actions):
    # Action filter
    action_filter = mo.ui.multiselect(
        options=unique_actions,
        label="アクションでフィルタ",
        max_selections=10
    )
    action_filter
    return (action_filter,)


@app.cell
def _(mo):
    # Text search
    search_text = mo.ui.text(
        label="テキスト検索（アクション、ユーザー、リポジトリ）",
        placeholder="検索キーワード..."
    )
    search_text
    return (search_text,)


@app.cell
def _(action_filter, alt, df, mo, pl, search_text):
    # Apply filters
    filtered_df = df

    if action_filter.value:
        filtered_df = filtered_df.filter(pl.col("action").is_in(action_filter.value))

    if search_text.value:
        search_term = search_text.value.lower()
        filtered_df = filtered_df.filter(
            pl.col("action").str.to_lowercase().str.contains(search_term) |
            pl.col("actor").str.to_lowercase().str.contains(search_term) |
            pl.col("repo").str.to_lowercase().str.contains(search_term)
        )

    # Action summary
    action_summary = (
        filtered_df.group_by("action")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    mo.md(f"""
    ## 🔍 フィルタ結果

    - **マッチしたイベント**: {len(filtered_df):,}
    - **アクション種類**: {len(action_summary)}
    """)
    return action_summary, filtered_df, search_term


@app.cell
def _(action_summary, alt, mo):
    # Action distribution chart
    if len(action_summary) > 0:
        action_chart = alt.Chart(action_summary.head(20).to_pandas()).mark_bar().encode(
            x=alt.X("count:Q", title="件数"),
            y=alt.Y("action:N", sort="-x", title="アクション"),
            color=alt.Color("count:Q", scale=alt.Scale(scheme="viridis")),
            tooltip=["action", "count"]
        ).properties(
            title="アクション分布（上位20件）",
            width=600,
            height=400
        )

        mo.ui.altair_chart(action_chart)
    else:
        mo.md("マッチするイベントがありません")
    return (action_chart,)


@app.cell
def _(mo):
    mo.md("## 📝 イベント詳細")
    return


@app.cell
def _(filtered_df, mo):
    # Show filtered data table
    if len(filtered_df) > 0:
        mo.ui.table(
            filtered_df.sort("timestamp", descending=True).head(100).to_pandas(),
            pagination=True,
            page_size=20
        )
    else:
        mo.md("表示するデータがありません")
    return


@app.cell
def _(mo):
    mo.md("## 📦 リポジトリ別集計")
    return


@app.cell
def _(alt, filtered_df, mo, pl):
    # Repository summary
    repo_summary = (
        filtered_df.filter(pl.col("repo").is_not_null())
        .group_by("repo")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(15)
    )

    if len(repo_summary) > 0:
        repo_chart = alt.Chart(repo_summary.to_pandas()).mark_bar().encode(
            x=alt.X("count:Q", title="イベント数"),
            y=alt.Y("repo:N", sort="-x", title="リポジトリ"),
            tooltip=["repo", "count"]
        ).properties(
            title="リポジトリ別イベント数（上位15件）",
            width=600,
            height=300
        )

        mo.ui.altair_chart(repo_chart)
    else:
        mo.md("リポジトリ情報がありません")
    return repo_chart, repo_summary


if __name__ == "__main__":
    app.run()
