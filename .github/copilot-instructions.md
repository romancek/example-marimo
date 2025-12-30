# GitHub Copilot Instructions

このドキュメントは、GitHub Copilotがこのプロジェクトのコンテキストを理解し、
適切なコード提案を行うための指示を定義します。

## プロジェクト概要

**GitHub Organization Audit Log Analyzer** - 監査ログ分析ツール

- **言語**: Python 3.12+
- **パッケージマネージャー**: uv
- **ノートブック**: marimo
- **データ処理**: Polars
- **可視化**: Altair

## アーキテクチャ

```
notebooks/             # marimoノートブック（メインコンテンツ）
├── index.py           # ダッシュボード・ナビゲーション
├── user_activity.py   # ユーザー分析
├── time_analysis.py   # 時系列分析
├── action_tracker.py  # アクション追跡
└── anomaly_detection.py # 異常検知
```

**公開方法**: `marimo export html-wasm` → GitHub Pages

## コーディング規約

### 全般

- **フォーマッター**: Ruff（`ruff format`）
- **リンター**: Ruff（`ruff check`）
- **行長**: 88文字
- **インデント**: スペース4つ
- **クォート**: ダブルクォート `"` を使用

### インポート順序

```python
# 1. 標準ライブラリ
import json
from datetime import datetime

# 2. サードパーティ
import marimo as mo
import polars as pl
import altair as alt
```

## marimoノートブックの書き方

### 基本構造

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
# ]
# ///
"""ノートブックの説明。"""

import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import altair as alt
    import json
    from datetime import datetime
    return mo, pl, alt, json, datetime


@app.cell
def _(mo):
    title = mo.md(r"""
    # タイトル

    説明テキスト
    """)
    title  # 必ず結果を返すか評価する
    return (title,)
```

### 重要なルール

1. **結果の表示**: `mo.md()`, `mo.ui.*()` の結果は**必ずセルの最後で返すか評価する**
1. **変数名の一意性**: セル間で同じ変数名を使わない（`result`ではなく`user_result`など）
1. **mo.stop()の活用**: 条件分岐は`mo.stop()`を使用

```python
# ✅ Good: 結果を返す
@app.cell
def _(mo):
    title = mo.md("# タイトル")
    title  # 評価して表示
    return (title,)

# ❌ Bad: 結果を返さない（表示されない）
@app.cell
def _(mo):
    mo.md("# タイトル")
    return
```

### ファイルアップロード

```python
@app.cell
def _(mo):
    file_input = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        label="監査ログファイルを選択",
    )
    file_input
    return (file_input,)


@app.cell
def _(file_input, mo, pl, json):
    mo.stop(not file_input.value, mo.md("ファイルを選択してください"))

    content = file_input.value[0].contents.decode("utf-8")
    content = content.strip()

    if content.startswith("["):
        data = json.loads(content)
    else:
        data = [json.loads(line) for line in content.split("\n") if line.strip()]

    df = pl.DataFrame(data)
    return (df,)
```

### UI要素のベストプラクティス

```python
# ✅ Good: 説明的なラベル
slider = mo.ui.slider(1, 100, value=10, label="表示件数")

# ✅ Good: mo.stop()で条件分岐
mo.stop(not file_input.value, mo.md("ファイルを選択してください"))

# ❌ Bad: 通常のif文で早期リターン
if not file_input.value:
    return
```

## Polarsパターン

### 基本的な集計

```python
# ユーザー別カウント
user_counts = (
    df.group_by("actor")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .head(20)
)
```

### タイムスタンプ処理

```python
# ミリ秒タイムスタンプを変換
df = df.with_columns([
    (pl.col("@timestamp") // 1000)
    .cast(pl.Datetime("ms"))
    .alias("timestamp")
])
```

## Altairパターン

### 基本的なチャート

```python
chart = (
    alt.Chart(df.to_pandas())
    .mark_bar()
    .encode(
        x=alt.X("actor:N", sort="-y", title="ユーザー"),
        y=alt.Y("count:Q", title="アクション数"),
        tooltip=["actor", "count"],
    )
    .properties(width=600, height=400)
)
```

## 禁止事項

- ❌ `print()` デバッグ（`mo.md()` を使用）
- ❌ グローバル変数の変更
- ❌ 裸の `except:` 句
- ❌ 本番データのハードコード
- ❌ `mo.md()`や`mo.ui.*`の結果を返さない

## 参考リンク

- [marimo Documentation](https://docs.marimo.io/)
- [Polars User Guide](https://docs.pola.rs/)
- [Altair Documentation](https://altair-viz.github.io/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
