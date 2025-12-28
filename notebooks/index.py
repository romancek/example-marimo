# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
#     "pydantic",
# ]
# ///
"""
GitHub Organization Audit Log Analyzer - Index Page

This is the main entry point for the audit log analysis tool.
Navigate to different analysis views from here.
"""

import marimo


__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # 🔍 GitHub Organization Audit Log Analyzer

    GitHub OrganizationのAudit Logを分析するためのインタラクティブツールです。

    ## 📊 分析メニュー

    以下のノートブックから分析を開始できます：
    """)


@app.cell
def _(mo):
    # Navigation cards
    nav_cards = mo.vstack(
        [
            mo.hstack(
                [
                    mo.md("""
            ### 👥 ユーザー別アクティビティ
            [`user_activity.py`](./user_activity.py)

            - ユーザー別のアクション数
            - 最もアクティブなユーザー
            - ユーザーごとのアクション種別分布
            """),
                    mo.md("""
            ### 📈 時系列分析
            [`time_analysis.py`](./time_analysis.py)

            - 時間帯別アクティビティ
            - 日次/週次/月次トレンド
            - ピーク時間帯の特定
            """),
                ]
            ),
            mo.hstack(
                [
                    mo.md("""
            ### 🔎 アクション追跡
            [`action_tracker.py`](./action_tracker.py)

            - アクション種別でフィルタリング
            - 特定イベントの詳細検索
            - リポジトリ/チーム別集計
            """),
                    mo.md("""
            ### ⚠️ 異常検知
            [`anomaly_detection.py`](./anomaly_detection.py)

            - 時間外アクティビティ
            - 大量操作の検出
            - 危険なアクションの警告
            """),
                ]
            ),
        ]
    )
    nav_cards


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## 📁 データの読み込み

    分析を始めるには、まずAudit LogのJSONファイルをアップロードしてください。
    """)


@app.cell
def _(mo):
    file_upload = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        multiple=False,
        label="Audit Logファイルをアップロード",
    )
    file_upload
    return (file_upload,)


@app.cell
def _(file_upload, mo):
    # Show upload status
    if file_upload.value:
        file_info = file_upload.value[0]
        mo.md(f"""
        ✅ **ファイルがアップロードされました**

        - ファイル名: `{file_info.name}`
        - サイズ: {len(file_info.contents) / 1024:.1f} KB
        """)
    else:
        mo.md("⏳ ファイルを選択してください...")


@app.cell
def _(mo):
    mo.md(r"""
    ---

    ## ℹ️ このツールについて

    このツールは以下の技術スタックで構築されています：

    - **marimo**: リアクティブノートブック
    - **Polars**: 高速DataFrame処理
    - **DuckDB**: 分析用データベース（大規模データ用）
    - **Altair**: インタラクティブ可視化
    - **Pydantic**: データバリデーション

    ### データ規模

    - 最大330万イベント（3年分）に対応
    - メモリ効率の良いストリーミング処理をサポート
    """)


if __name__ == "__main__":
    app.run()
