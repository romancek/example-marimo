# 新しい marimo 分析ノートブックの作成

このプロンプトを使用して、新しい分析ノートブックを作成してください。

## 入力情報

作成するノートブックについて以下を指定してください：

- **ノートブック名**: {{notebook_name}}
- **分析目的**: {{purpose}}
- **必要なデータ**: {{required_data}}
- **主要な可視化**: {{visualizations}}

## テンプレート

以下のテンプレートに基づいてノートブックを生成してください：

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
#     "pydantic",
# ]
# ///
"""{{notebook_name}} - {{purpose}}

このノートブックでは、GitHub監査ログの{{purpose}}を行います。
"""

import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import altair as alt
    from datetime import datetime
    from pathlib import Path

    from audit_analyzer.loader import load_audit_log
    from audit_analyzer.models import AuditLogEntry
    return mo, pl, alt, datetime, Path, load_audit_log, AuditLogEntry


@app.cell
def _(mo):
    mo.md(r"""
    # {{notebook_name}}

    {{purpose}}

    ## 使い方

    1. 監査ログファイル（JSON/NDJSON）をアップロード
    2. フィルタ条件を設定
    3. 分析結果を確認
    """)
    return


@app.cell
def _(mo):
    # ファイル入力UI
    file_input = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        label="📁 監査ログファイルを選択",
        multiple=False,
    )
    file_input
    return (file_input,)


@app.cell
def _(file_input, mo, load_audit_log):
    # ファイル読み込み
    mo.stop(
        not file_input.value,
        mo.md("⬆️ ファイルをアップロードしてください")
    )

    import tempfile
    import os

    # 一時ファイルに保存して読み込み
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".json"
    ) as tmp:
        tmp.write(file_input.value[0].contents)
        tmp_path = tmp.name

    try:
        df = load_audit_log(tmp_path)
        mo.md(f"✅ **{len(df):,}** 件のログエントリを読み込みました")
    finally:
        os.unlink(tmp_path)
    return (df,)


@app.cell
def _(mo):
    mo.md(r"""
    ## フィルタ設定
    """)
    return


@app.cell
def _(mo, df, pl):
    # フィルタUI
    actors = sorted(df.select("actor").unique().drop_nulls().to_series().to_list())
    actions = sorted(df.select("action").unique().to_series().to_list())

    actor_select = mo.ui.multiselect(
        options=actors,
        label="ユーザー",
    )
    action_select = mo.ui.multiselect(
        options=actions[:50],  # 最大50件
        label="アクション",
    )

    mo.hstack([actor_select, action_select], justify="start")
    return actor_select, action_select


@app.cell
def _(df, actor_select, action_select, pl):
    # フィルタ適用
    filtered_df = df

    if actor_select.value:
        filtered_df = filtered_df.filter(
            pl.col("actor").is_in(actor_select.value)
        )

    if action_select.value:
        filtered_df = filtered_df.filter(
            pl.col("action").is_in(action_select.value)
        )

    return (filtered_df,)


@app.cell
def _(mo, filtered_df):
    mo.md(f"""
    ## 分析結果

    **フィルタ後のエントリ数**: {len(filtered_df):,} 件
    """)
    return


@app.cell
def _(filtered_df, alt):
    # TODO: {{visualizations}} の可視化を実装
    # 例: 時系列チャート、棒グラフ、ヒートマップなど

    chart = (
        alt.Chart(filtered_df.to_pandas())
        .mark_bar()
        .encode(
            x=alt.X("action:N", sort="-y"),
            y=alt.Y("count():Q"),
            tooltip=["action", "count()"],
        )
        .properties(
            title="アクション別件数",
            width=600,
            height=400,
        )
    )
    chart
    return (chart,)


@app.cell
def _(mo, filtered_df):
    # データテーブル
    mo.ui.table(
        filtered_df.head(100).to_pandas(),
        label="詳細データ（最大100件）",
    )
    return


if __name__ == "__main__":
    app.run()
```

## 生成ルール

1. **インポート**: 最初のセルで必要なライブラリをすべてインポート
2. **ヘッダー**: Markdownセルでノートブックの目的を説明
3. **ファイル入力**: `mo.ui.file()` でファイルアップロードUI
4. **データ読み込み**: `mo.stop()` でファイル選択前は停止
5. **フィルタUI**: `mo.ui.multiselect()` などでインタラクティブなフィルタ
6. **可視化**: Altairチャートを使用
7. **データテーブル**: `mo.ui.table()` で詳細データを表示

## チェックリスト

生成後、以下を確認してください：

- [ ] すべてのセルが `return` で適切に値を返している
- [ ] セル間の依存関係が正しい
- [ ] 型ヒントが付いている（必要な場合）
- [ ] エラーハンドリングが適切
- [ ] UIラベルが日本語で分かりやすい
