# GitHub Organization Audit Log Analyzer

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-blueviolet)](https://github.com/astral-sh/uv)
[![marimo](https://img.shields.io/badge/marimo-notebooks-orange)](https://marimo.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

GitHub OrganizationのAudit Log（JSON形式）を分析するためのインタラクティブツール。
[marimo](https://marimo.io/)ノートブックを使用し、**GitHub Pages**で公開可能なWASM版としてデプロイできます。

## 📋 目次

- [概要](#%E6%A6%82%E8%A6%81)
- [機能一覧](#-%E6%A9%9F%E8%83%BD%E4%B8%80%E8%A6%A7)
- [クイックスタート](#-%E3%82%AF%E3%82%A4%E3%83%83%E3%82%AF%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%88)
- [GitHub Pagesでの公開](#-github-pages%E3%81%A7%E3%81%AE%E5%85%AC%E9%96%8B)
- [開発環境セットアップ](#-%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E3%82%BB%E3%83%83%E3%83%88%E3%82%A2%E3%83%83%E3%83%97)
- [GitHub Audit Logの取得方法](#-github-audit-log%E3%81%AE%E5%8F%96%E5%BE%97%E6%96%B9%E6%B3%95)
- [技術スタック](#-%E6%8A%80%E8%A1%93%E3%82%B9%E3%82%BF%E3%83%83%E3%82%AF)
- [ライセンス](#-%E3%83%A9%E3%82%A4%E3%82%BB%E3%83%B3%E3%82%B9)

## 概要

このプロジェクトは、GitHub Organizationの監査ログを効率的に分析するためのツールです。

### ユースケース

- **セキュリティ監査**: 危険なアクション（削除、権限変更）の検出
- **コンプライアンス**: 組織ポリシーへの準拠状況の確認
- **運用分析**: ユーザーアクティビティの可視化とトレンド分析
- **インシデント調査**: 特定期間・ユーザーの活動追跡

## 🎯 機能一覧

| 機能               | 説明                                 | ノートブック           |
| ------------------ | ------------------------------------ | ---------------------- |
| **ダッシュボード** | ナビゲーション、ファイルアップロード | `index.py`             |
| **ユーザー別分析** | ユーザーごとのアクション数・分布     | `user_activity.py`     |
| **時系列分析**     | 時間帯別/日別/週別トレンド           | `time_analysis.py`     |
| **アクション追跡** | アクション種別フィルタ、検索         | `action_tracker.py`    |
| **異常検知**       | 危険アクション検出、大量操作警告     | `anomaly_detection.py` |

## 🚀 クイックスタート

### 前提条件

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)（推奨）

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/example-marimo.git
cd example-marimo
```

### 2. 依存関係のインストール

```bash
uv sync
```

### 3. ノートブックの起動

```bash
# メインのダッシュボードを開く
uv run marimo edit notebooks/index.py

# または特定の分析ノートブック
uv run marimo edit notebooks/user_activity.py
uv run marimo edit notebooks/time_analysis.py
uv run marimo edit notebooks/anomaly_detection.py
uv run marimo edit notebooks/action_tracker.py
```

## 🌐 GitHub Pagesでの公開

marimoノートブックをWASM-Powered HTMLとしてエクスポートし、GitHub Pagesで公開できます。

### HTMLエクスポート

```bash
# 単一ノートブックをエクスポート
uv run marimo export html-wasm notebooks/index.py -o dist/index.html --mode run

# 全ノートブックをエクスポート
for nb in notebooks/*.py; do
  name=$(basename "$nb" .py)
  uv run marimo export html-wasm "$nb" -o "dist/${name}.html" --mode run
done
```

### GitHub Actionsでの自動デプロイ

`.github/workflows/deploy.yml` を作成してGitHub Pagesに自動デプロイできます。

## 🛠 開発環境セットアップ

### 完全セットアップ

```bash
# 1. uvのインストール（まだの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 依存関係のインストール
uv sync

# 3. pre-commitフックの設定
uv run pre-commit install

# 4. コード品質チェック
uv run pre-commit run --all-files
```

### コード品質チェック

```bash
# フォーマット
uv run ruff format .

# リント
uv run ruff check . --fix
```

## 📁 ディレクトリ構造

```
example-marimo/
├── notebooks/                  # marimo ノートブック
│   ├── index.py               # ダッシュボード（メインページ）
│   ├── user_activity.py       # ユーザー別アクティビティ分析
│   ├── time_analysis.py       # 時系列・トレンド分析
│   ├── action_tracker.py      # アクション検索・追跡
│   └── anomaly_detection.py   # 異常検知・アラート
│
├── data/                       # データファイル（.gitignore対象）
│
├── docs/                       # ドキュメント
│   ├── DESIGN.md              # 設計書
│   └── copilot/               # GitHub Copilot用計画書
│
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/
│   └── workflows/
│
├── pyproject.toml             # 依存関係定義
├── .pre-commit-config.yaml    # pre-commitフック設定
└── .gitignore
```

## 📥 GitHub Audit Logの取得方法

### 方法1: GitHub CLI（推奨）

```bash
# GitHub CLIのインストール
brew install gh  # macOS

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

詳細: [GitHub Docs - Audit Log API](https://docs.github.com/en/rest/orgs/orgs#get-the-audit-log-for-an-organization)

## 🔧 技術スタック

| カテゴリ       | ライブラリ | バージョン |
| -------------- | ---------- | ---------- |
| ノートブック   | marimo     | ≥0.18.0    |
| DataFrame      | Polars     | ≥1.18.0    |
| 可視化         | Altair     | ≥5.5.0     |
| パッケージ管理 | uv         | latest     |
| リンター       | Ruff       | ≥0.8.0     |

## 🔒 セキュリティに関する注意

- Audit Logデータには**機密情報**（IPアドレス、ユーザー名等）が含まれます
- `data/` ディレクトリは `.gitignore` で除外されています
- **本番データをコミットしないでください**

## 📝 ライセンス

このプロジェクトは [MIT License](./LICENSE) の下で公開されています。
