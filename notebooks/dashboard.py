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
    import sys

    # WASM環境(GitHub Pages)かローカル環境かを判定
    is_wasm = sys.platform == "emscripten"

    # Navigation cards with HTML links
    def make_nav_card(title: str, icon: str, filename: str, features: list[str]):
        feature_list = "\n".join(f"- {f}" for f in features)
        # 環境に応じてリンク形式を切り替え
        if is_wasm:
            # GitHub Pages - static HTML file link
            link_url = filename.replace(".py", ".html")
        else:
            # Local environment - marimo file parameter
            link_url = f"/?file=notebooks/{filename}"
        return mo.vstack(
            [
                mo.md(f"### {icon} {title}"),
                mo.Html(
                    f'<a href="{link_url}" '
                    f'style="display:inline-block;padding:8px 16px;background:#6366f1;'
                    f'color:white;border-radius:6px;text-decoration:none;font-size:14px;">'
                    f"📂 {title} を開く</a>"
                ),
                mo.md(feature_list),
            ],
            align="start",
        )

    nav_cards = mo.vstack(
        [
            mo.hstack(
                [
                    make_nav_card(
                        "ユーザー別アクティビティ",
                        "👥",
                        "user_activity.py",
                        [
                            "ユーザー別のアクション数",
                            "最もアクティブなユーザー",
                            "ユーザーごとのアクション種別分布",
                        ],
                    ),
                    make_nav_card(
                        "時系列分析",
                        "📈",
                        "time_analysis.py",
                        [
                            "時間帯別アクティビティ",
                            "日次/週次/月次トレンド",
                            "ピーク時間帯の特定",
                        ],
                    ),
                ],
                justify="start",
                gap=2,
            ),
            mo.hstack(
                [
                    make_nav_card(
                        "アクション追跡",
                        "🔎",
                        "action_tracker.py",
                        [
                            "アクション種別でフィルタリング",
                            "特定イベントの詳細検索",
                            "リポジトリ/チーム別集計",
                        ],
                    ),
                    make_nav_card(
                        "異常検知",
                        "⚠️",
                        "anomaly_detection.py",
                        [
                            "時間外アクティビティ",
                            "大量操作の検出",
                            "危険なアクションの警告",
                        ],
                    ),
                ],
                justify="start",
                gap=2,
            ),
        ]
    )
    nav_cards


@app.cell
def _(mo):
    mo.md(r"""
    ---
    # 📝サマリ表示
    ## 📁 データの読み込み

    分析を始めるには、Audit LogのJSONファイルをアップロードしてください。
    **複数ファイルを選択して一括読み込みも可能です。**
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
def _(file_upload, mo):
    import json
    from datetime import datetime

    import polars as pl

    def parse_audit_log_file(file_info) -> list[dict]:
        """単一ファイルをパースしてレコードリストを返す"""
        content = file_info.contents.decode("utf-8").strip()

        # NDJSON形式 または JSON配列形式を判定
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
                    "_source_file": file_info.name,  # ソースファイル追跡用
                }
            )
        return records

    # 複数ファイルの読み込み
    df = None
    if file_upload.value:
        all_records = []
        file_summaries = []
        total_size = 0

        for file_info in file_upload.value:
            records = parse_audit_log_file(file_info)
            all_records.extend(records)
            file_summaries.append(f"- `{file_info.name}`: {len(records):,} イベント")
            total_size += len(file_info.contents)

        df = pl.DataFrame(all_records)

        # ファイル数に応じたメッセージ
        file_count = len(file_upload.value)
        files_info = "\n".join(file_summaries)

        status = mo.md(f"""
        ✅ **{len(df):,} イベントを読み込みました** ({file_count} ファイル)

        **読み込んだファイル:**
        {files_info}

        **サマリ:**
        - 合計サイズ: {total_size / 1024:.1f} KB
        - 期間: {df["timestamp"].min()} 〜 {df["timestamp"].max()}
        - ユニークユーザー: {df["actor"].n_unique()} 人
        - ユニークアクション: {df["action"].n_unique()} 種類
        """)
    else:
        df = None
        status = mo.md("⏳ ファイルを選択してください...")
    status


@app.cell
def _(mo):
    mo.md(r"""
    # 📊カスタム分析🧐
    以降ではDataFrame型のdf変数を使って自由に分析してください！
    """)


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
