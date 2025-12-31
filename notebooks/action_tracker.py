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
Action Tracker

Track and filter specific actions in the audit log:
- Filter by action type
- Search specific events
- Repository/team-level aggregation
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
    # 🔎 アクション追跡

    特定のアクションを追跡・フィルタリングします。
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
                    "org": entry.get("org", "unknown"),
                    "repo": entry.get("repo"),
                    "user": entry.get("user"),
                    "team": entry.get("team"),
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
    # Get unique actions
    unique_actions = (
        df.select(pl.col("action").unique()).sort("action")["action"].to_list()
    )

    mo.md(f"## 📋 アクション一覧 ({len(unique_actions)} 種類)")
    return (unique_actions,)


@app.cell
def _(mo, unique_actions):
    # Action filter
    action_filter = mo.ui.multiselect(
        options=unique_actions, label="アクションでフィルタ", max_selections=10
    )
    action_filter
    return (action_filter,)


@app.cell
def _(mo):
    # Text search
    search_text = mo.ui.text(
        label="テキスト検索（アクション、ユーザー、リポジトリ）",
        placeholder="検索キーワード...",
    )
    search_text
    return (search_text,)


@app.cell
def _(action_filter, df, mo, pl, search_text):
    # Apply filters
    filtered_df = df

    if action_filter.value:
        filtered_df = filtered_df.filter(pl.col("action").is_in(action_filter.value))

    if search_text.value:
        search_term = search_text.value.lower()
        filtered_df = filtered_df.filter(
            pl.col("action").str.to_lowercase().str.contains(search_term)
            | pl.col("actor").str.to_lowercase().str.contains(search_term)
            | pl.col("repo").str.to_lowercase().str.contains(search_term)
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
    return action_summary, filtered_df


@app.cell
def _(action_summary, alt, mo):
    # Action distribution chart
    if len(action_summary) > 0:
        action_chart = (
            alt.Chart(action_summary.head(20).to_dicts())
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="件数"),
                y=alt.Y("action:N", sort="-x", title="アクション"),
                color=alt.Color("count:Q", scale=alt.Scale(scheme="viridis")),
                tooltip=["action:N", "count:Q"],
            )
            .properties(title="アクション分布（上位20件）", width=600, height=400)
        )
        filter_result = mo.ui.altair_chart(action_chart)
    else:
        action_chart = None
        filter_result = mo.md("マッチするイベントがありません")

    filter_result
    return (action_chart,)


@app.cell
def _(mo):
    mo.md("""
    ## 📝 イベント詳細
    """)


@app.cell
def _(filtered_df, mo):
    # Show filtered data table
    if len(filtered_df) > 0:
        table_result = mo.ui.table(
            filtered_df.sort("timestamp", descending=True).head(100),
            pagination=True,
            page_size=20,
        )
    else:
        table_result = mo.md("表示するデータがありません")

    table_result


@app.cell
def _(mo):
    mo.md("""
    ## 📦 リポジトリ別集計
    """)


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
        repo_chart = (
            alt.Chart(repo_summary.to_dicts())
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="イベント数"),
                y=alt.Y("repo:N", sort="-x", title="リポジトリ"),
                tooltip=["repo:N", "count:Q"],
            )
            .properties(
                title="リポジトリ別イベント数（上位15件）", width=600, height=300
            )
        )
        repo_result = mo.ui.altair_chart(repo_chart)
    else:
        repo_result = mo.md("リポジトリ情報がありません")

    repo_result


if __name__ == "__main__":
    app.run()
