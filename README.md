# GitHub Organization Audit Log Analyzer

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-blueviolet)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

GitHub OrganizationのAudit Log（JSON形式）を分析するためのインタラクティブツール。
[marimo](https://marimo.io/)ノートブックを使用し、サーバー版（開発者向け）とWASM版（非技術者向け、GitHub Pages配布）の両方をサポートします。

## 📋 目次

- [概要](#概要)
- [機能一覧](#-機能一覧)
- [クイックスタート](#-クイックスタート)
- [開発環境セットアップ](#-開発環境セットアップ)
- [ディレクトリ構造](#-ディレクトリ構造)
- [GitHub Audit Logの取得方法](#-github-audit-logの取得方法)
- [技術スタック](#-技術スタック)
- [ライセンス](#-ライセンス)

## 概要

このプロジェクトは、GitHub Organizationの監査ログを効率的に分析するためのツールです。

### ユースケース

- **セキュリティ監査**: 危険なアクション（削除、権限変更）の検出
- **コンプライアンス**: 組織ポリシーへの準拠状況の確認
- **運用分析**: ユーザーアクティビティの可視化とトレンド分析
- **インシデント調査**: 特定期間・ユーザーの活動追跡

### 設計原則

- **型安全**: Pydanticによる厳密なバリデーション
- **高パフォーマンス**: DuckDB/Polarsによる大規模データ対応（300万件以上）
- **インタラクティブ**: marimoによるリアクティブUI
- **再利用性**: コアロジックをライブラリとして分離

## 🎯 機能一覧

| 機能 | 説明 | ノートブック |
|------|------|-------------|
| **ユーザー別分析** | ユーザーごとのアクション数・分布、アクティブユーザー特定 | `user_activity.py` |
| **時系列分析** | 時間帯別/日別/週別トレンド、ピーク時間特定 | `time_analysis.py` |
| **アクション追跡** | アクション種別フィルタ、テキスト検索、集計 | `action_tracker.py` |
| **異常検知** | 危険アクション検出、大量操作警告、異常IP検出 | `anomaly_detection.py` |

## 🚀 クイックスタート

### 前提条件

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (推奨) または pip

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/audit-analyzer.git
cd audit-analyzer
```

### 2. 依存関係のインストール

```bash
# uvを使用（推奨・高速）
uv sync

# または pip
pip install -e ".[dev,test]"
```

### 3. ノートブックの起動

```bash
# メインのダッシュボードを開く
uv run marimo edit notebooks/index.py --no-sandbox

# または特定の分析ノートブック
uv run marimo edit notebooks/user_activity.py --no-sandbox
uv run marimo edit notebooks/time_analysis.py --no-sandbox
uv run marimo edit notebooks/anomaly_detection.py --no-sandbox
```

### 4. テストの実行

```bash
uv run pytest
```

## 🛠 開発環境セットアップ

### 完全セットアップ

```bash
# 1. uvのインストール（まだの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 依存関係のインストール（開発用ツール含む）
uv sync --all-extras

# 3. pre-commitフックの設定
uv run pre-commit install

# 4. テストの実行
uv run pytest --cov

# 5. 型チェック
uv run mypy src/
```

### テストデータの生成

```bash
# 10,000件のテストデータを生成
uv run python scripts/generate_test_data.py --output data/test_audit_log.json --count 10000

# NDJSON形式で100,000件（大規模テスト用）
uv run python scripts/generate_test_data.py --output data/large_test.ndjson --count 100000 --format ndjson
```

### コード品質チェック

```bash
# フォーマット
uv run ruff format .

# リント
uv run ruff check . --fix

# 型チェック
uv run mypy src/
```

## 📁 ディレクトリ構造

```
audit-analyzer/
├── src/
│   └── audit_analyzer/         # コアライブラリ
│       ├── __init__.py         # パッケージ初期化
│       ├── py.typed            # PEP 561 型マーカー
│       ├── models.py           # Pydanticデータモデル
│       ├── loader.py           # データローダー（Eager/Lazy/Streaming）
│       ├── analyzers/          # 分析エンジン
│       │   ├── __init__.py
│       │   ├── base.py         # 基底アナライザークラス
│       │   ├── user_activity.py
│       │   ├── time_series.py
│       │   └── anomaly.py
│       └── utils/
│           ├── __init__.py
│           └── constants.py    # 定数・設定値
│
├── notebooks/                  # marimo ノートブック
│   ├── index.py               # ダッシュボード（メインページ）
│   ├── user_activity.py       # ユーザー別アクティビティ分析
│   ├── time_analysis.py       # 時系列・トレンド分析
│   ├── action_tracker.py      # アクション検索・追跡
│   └── anomaly_detection.py   # 異常検知・アラート
│
├── tests/                      # テストスイート
│   ├── conftest.py            # pytest設定・共通フィクスチャ
│   ├── fixtures/
│   │   └── sample_audit_log.json
│   ├── test_models.py         # モデル単体テスト
│   ├── test_loader.py         # ローダーテスト
│   └── test_analyzers.py      # アナライザーテスト
│
├── scripts/
│   └── generate_test_data.py  # テストデータ生成スクリプト
│
├── data/                       # データファイル（.gitignore対象）
├── docs/                       # ドキュメント
│   └── DESIGN.md              # 設計書
│
├── .github/
│   ├── copilot-instructions.md # Copilot用プロジェクト指示
│   ├── prompts/               # 再利用可能なプロンプト
│   │   ├── new-notebook.md
│   │   └── add-model.md
│   └── workflows/             # GitHub Actions
│
├── .vscode/
│   ├── extensions.json        # 推奨拡張機能
│   └── settings.json          # ワークスペース設定
│
├── pyproject.toml             # プロジェクト設定・依存関係
├── .pre-commit-config.yaml    # pre-commitフック設定
├── .python-version            # Pythonバージョン指定
└── .gitignore
```

## 📥 GitHub Audit Logの取得方法

### 方法1: GitHub CLI（推奨）

```bash
# GitHub CLIのインストール
brew install gh  # macOS
# または https://cli.github.com/

# 認証
gh auth login

# 監査ログのエクスポート（過去90日間）
gh api \
  -H "Accept: application/vnd.github+json" \
  --paginate \
  /orgs/{org}/audit-log \
  > data/audit_log.json
```

### 方法2: REST API

```bash
# Personal Access Token (PAT) が必要
# 必要なスコープ: read:audit_log

curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.github.com/orgs/{org}/audit-log" \
  > data/audit_log.json
```

### 方法3: Enterprise Server（オンプレミス）

```bash
# Enterprise Server管理者向け
curl -L \
  -H "Authorization: token YOUR_TOKEN" \
  "https://HOSTNAME/api/v3/enterprises/{enterprise}/audit-log" \
  > data/audit_log.json
```

### 取得パラメータ

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `phrase` | 検索クエリ | `action:repo.create` |
| `include` | 追加フィールド | `web`, `git`, `all` |
| `after` | カーソルベースのページネーション | `MS4yNTI...` |
| `per_page` | 1ページあたりの結果数 | `100` (最大) |

詳細: [GitHub Docs - Audit Log API](https://docs.github.com/en/rest/orgs/orgs#get-the-audit-log-for-an-organization)

## 🔧 技術スタック

| カテゴリ | ライブラリ | バージョン | WASM対応 |
|---------|-----------|-----------|----------|
| ノートブック | marimo | ≥0.18.0 | ✅ |
| DataFrame | Polars | ≥1.18.0 | ❌ |
| DataFrame (WASM) | Pandas | ≥2.2.0 | ✅ |
| DB | DuckDB | ≥1.2.0 | ❌ |
| バリデーション | Pydantic | ≥2.10.0 | ✅ |
| 可視化 | Altair | ≥5.5.0 | ✅ |
| パッケージ管理 | uv | latest | - |
| リンター | Ruff | ≥0.8.0 | - |
| テスト | pytest | ≥8.3.0 | - |

### WASM版の制限事項

⚠️ **重要**: Pyodide (WASM) では Polars と DuckDB は動作しません。

WASM版を作成する場合は、以下の対応が必要です：

1. **Pandasへのフォールバック**: ノートブック内で `pandas` を使用
2. **Narwhals の検討**: Polars/Pandas の抽象化レイヤー
3. **データサイズの制限**: ブラウザメモリの制約

### WASM版のデプロイ (GitHub Pages)

```bash
# WASMとしてエクスポート
uv run marimo export html-wasm notebooks/index.py -o dist/ --mode run

# GitHub Pagesにデプロイ（.github/workflows/deploy.yml を設定）
```

## 🔒 セキュリティに関する注意

- Audit Logデータには**機密情報**（IPアドレス、ユーザー名等）が含まれます
- `data/` ディレクトリは `.gitignore` で除外されています
- **本番データをコミットしないでください**
- 分析結果の共有時は個人情報をマスキングしてください

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

### コード品質基準

- Ruffによるフォーマット・リントの通過
- mypyによる型チェックの通過
- テストカバレッジ80%以上
- ドキュメント文字列の記述

## 📝 ライセンス

このプロジェクトは [MIT License](./LICENSE) の下で公開されています。
