# GitHub Organization Audit Log 分析システム設計書

## 1. 概要

本ドキュメントでは、GitHub OrganizationのAudit Log（JSON形式）を効率的に分析するためのシステム設計について説明します。

### 1.1 要件

- **データ規模**: 1日約3,000イベント × 365日 × 3年 = 約330万イベント（3-4GB）
- **入力形式**: JSON / NDJSON（Newline-delimited JSON）
- **分析機能**:
  - ユーザー活動分析
  - 時間帯別分析
  - アクション追跡
  - 異常検知
- **公開方法**: GitHub Pages（WASM-Powered HTML）

### 1.2 技術スタック

| コンポーネント | 選定理由 |
|-------------|---------|
| **marimo** | リアクティブノートブック、WASM対応 |
| **Polars** | Rust製の高速DataFrame |
| **Altair** | Vega-Lite基盤の宣言的可視化 |

---

## 2. アーキテクチャ

### 2.1 シンプルなノートブック中心設計

```
┌─────────────────────────────────────────────────────────────┐
│                    notebooks/                                │
├─────────────────────────────────────────────────────────────┤
│  index.py           - ダッシュボード・ナビゲーション        │
│  user_activity.py   - ユーザー別アクティビティ分析          │
│  time_analysis.py   - 時系列・トレンド分析                  │
│  action_tracker.py  - アクション検索・追跡                  │
│  anomaly_detection.py - 異常検知・アラート                  │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                    marimo export                             │
│            html-wasm（WASM-Powered HTML）                   │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Pages                              │
│              （静的ファイルホスティング）                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 設計原則

1. **スタンドアロン**: 各ノートブックは独立して動作
2. **PEP 723準拠**: インライン依存関係でサンドボックス環境を構築
3. **シンプル**: 外部パッケージへの依存なし（notebooks/のみ）

---

## 3. ノートブック設計

### 3.1 共通パターン

各ノートブックは以下の構造を持ちます：

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
# ]
# ///
"""ノートブックの説明"""

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
    # ファイルアップロード
    file_input = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        label="監査ログファイルを選択",
    )
    file_input
    return (file_input,)


@app.cell
def _(file_input, pl, json):
    # データ読み込み
    mo.stop(not file_input.value, mo.md("ファイルを選択してください"))

    content = file_input.value[0].contents.decode("utf-8")
    # JSON / NDJSON の判定と読み込み
    ...
    return (df,)
```

### 3.2 各ノートブックの役割

| ノートブック | 主な機能 |
|-------------|---------|
| `index.py` | ナビゲーション、ファイルアップロード、データ概要 |
| `user_activity.py` | ユーザー別集計、Top Nユーザー、アクション内訳 |
| `time_analysis.py` | 時間帯別分布、曜日別分布、日次トレンド |
| `action_tracker.py` | アクション種別フィルタ、リポジトリ別集計 |
| `anomaly_detection.py` | 危険アクション検出、時間外活動、バルク操作 |

---

## 4. データ処理

### 4.1 JSON/NDJSON読み込み

```python
def load_audit_data(content: str) -> pl.DataFrame:
    """JSON/NDJSONを自動判定して読み込み"""
    content = content.strip()

    if content.startswith("["):
        # JSON配列形式
        data = json.loads(content)
    else:
        # NDJSON形式
        data = [json.loads(line) for line in content.split("\n") if line.strip()]

    return pl.DataFrame(data)
```

### 4.2 タイムスタンプ処理

GitHub Audit Logのタイムスタンプは複数の形式があります：

```python
def parse_timestamp(df: pl.DataFrame) -> pl.DataFrame:
    """タイムスタンプを統一形式に変換"""
    return df.with_columns([
        pl.when(pl.col("@timestamp").cast(pl.Utf8).str.contains(r"^\d+$"))
        .then(pl.col("@timestamp").cast(pl.Int64) // 1000)  # ミリ秒
        .otherwise(pl.col("@timestamp"))
        .cast(pl.Datetime)
        .alias("timestamp")
    ])
```

---

## 5. 可視化

### 5.1 Altairによるチャート

```python
def create_activity_chart(df: pl.DataFrame) -> alt.Chart:
    """ユーザーアクティビティチャート"""
    return (
        alt.Chart(df.to_pandas())
        .mark_bar()
        .encode(
            x=alt.X("actor:N", sort="-y", title="ユーザー"),
            y=alt.Y("count:Q", title="アクション数"),
            color=alt.Color("action:N", title="アクション"),
            tooltip=["actor", "action", "count"],
        )
        .properties(width=600, height=400)
    )
```

### 5.2 インタラクティブUI

marimoのUI要素を活用：

```python
# スライダー
limit_slider = mo.ui.slider(1, 100, value=20, label="表示件数")

# ドロップダウン
action_filter = mo.ui.dropdown(
    options=["すべて"] + df["action"].unique().to_list(),
    value="すべて",
    label="アクション種別",
)

# チェックボックス
show_bots = mo.ui.checkbox(label="Botを含める", value=False)
```

---

## 6. デプロイ

### 6.1 WASM-Powered HTMLエクスポート

```bash
# 単一ノートブック
uv run marimo export html-wasm notebooks/index.py \
  -o dist/index.html \
  --mode run

# 全ノートブック
for nb in notebooks/*.py; do
  name=$(basename "$nb" .py)
  uv run marimo export html-wasm "$nb" \
    -o "dist/${name}.html" \
    --mode run
done
```

### 6.2 GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Export notebooks
        run: |
          uv sync
          mkdir -p dist
          for nb in notebooks/*.py; do
            name=$(basename "$nb" .py)
            uv run marimo export html-wasm "$nb" \
              -o "dist/${name}.html" \
              --mode run
          done

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```

---

## 7. セキュリティ考慮事項

### 7.1 データの取り扱い

- Audit Logには**機密情報**（IPアドレス、ユーザー名）が含まれる
- `data/`ディレクトリは`.gitignore`で除外
- WASM版では**ブラウザ内で処理**（サーバーにデータ送信なし）

### 7.2 WASM版の制限

- ファイルサイズ: ブラウザメモリの制約（〜数百MB推奨）
- 処理速度: ネイティブ版より低速
- 一部ライブラリ: Pyodide非対応の可能性

---

## 8. 更新履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-29 | notebooks/中心のシンプルな構成に変更 |
