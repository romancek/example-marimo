# プロジェクト整理・リファクタリング計画

**作成日**: 2025-12-29  
**ステータス**: ✅ Phase 1-3 完了  
**担当**: GitHub Copilot + User

---

## 📋 目次

- [0. コードベース調査結果](#0-コードベース調査結果)
- [1. リファクタリング作業計画](#1-リファクタリング作業計画)
- [2. 詳細TODO](#2-詳細todo)
- [3. marimoノートブックテスト戦略（将来）](#3-marimoノートブックテスト戦略将来)

---

## 実行履歴

### 2025-12-29 リファクタリング完了

**決定事項**:
- **Option B採用**: src/を削除、notebooks/を正とする
- **用途**: notebooks/のみ（GitHub Pages公開）
- **公開方法**: `marimo export html-wasm`

**実行した作業**:
1. ✅ `src/` ディレクトリを削除
2. ✅ `tests/` ディレクトリを削除
3. ✅ `pyproject.toml` からビルド設定・CLI設定を削除
4. ✅ `README.md` をnotebooks/中心の構成に更新
5. ✅ `docs/DESIGN.md` をシンプルな構成に更新
6. ✅ `.github/copilot-instructions.md` を更新
7. ✅ `.pre-commit-config.yaml` からmypy設定を削除
8. ✅ `.github/workflows/ci.yml` からtypecheck/test jobを削除
9. ✅ `.github/workflows/deploy.yml` のpathsトリガーを更新
10. ✅ `.github/prompts/` ディレクトリを削除

---

## 0. コードベース調査結果（参考）

### 🔍 調査日: 2025-12-29

### 0.1 旧プロジェクト構造（削除済み）

```
example-marimo/
├── src/audit_analyzer/     # ❌ 削除済み
│   ├── __init__.py
│   ├── models.py
│   ├── loader.py
│   ├── py.typed
│   ├── analyzers/
│   └── utils/
│
├── tests/                  # ❌ 削除済み
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_loader.py
│   └── test_analyzers.py
    ├── conftest.py         # フィクスチャ
    ├── test_models.py      # モデルテスト
    ├── test_loader.py      # ローダーテスト
    └── test_analyzers.py   # 分析エンジンテスト
```

---

### 0.2 重大な発見：src/ と notebooks/ の乖離 ⚠️

#### 📊 依存関係マトリクス

| 参照元 → 参照先 | src/audit_analyzer | notebooks/ | 外部ライブラリ |
|----------------|:-----------------:|:----------:|:-------------:|
| **notebooks/** | ❌ **未使用** | - | ✅ polars, altair, marimo |
| **tests/** | ✅ 使用 | ❌ 未テスト | ✅ pytest |
| **pyproject.toml** | ✅ ビルド対象 | ❌ 未定義 | ✅ 依存定義 |

#### 🚨 問題点

1. **notebooks/はsrc/を一切importしていない**
   - 全ノートブックが独自にJSON読み込み・分析ロジックを実装
   - 設計意図（コアロジックの再利用）が実現されていない

2. **コードの重複**
   ```
   機能                    notebooks/での実装    src/の対応
   ─────────────────────────────────────────────────────────
   JSON/NDJSON読み込み     各ノートブックで重複   loader.py
   データモデル            生dict → DataFrame    models.py (Pydantic)
   ユーザー分析            user_activity.py内    analyzers/user_activity.py
   時系列分析              time_analysis.py内    analyzers/time_series.py
   異常検知               anomaly_detection.py内 analyzers/anomaly.py
   ```

3. **テストカバレッジの不均衡**
   - `src/`: 38テスト（models, loader, analyzers）✅
   - `notebooks/`: 0テスト ❌

---

### 0.3 src/audit_analyzer の詳細分析

#### 定義されているクラス・関数

**models.py**:
| 定義 | 種別 | 説明 |
|------|------|------|
| `AuditAction` | StrEnum | GitHubアクションタイプ（500+種から主要定義） |
| `OperationType` | StrEnum | 操作タイプ（create/modify/remove/access） |
| `AuditLogEntry` | Pydantic Model | 監査ログエントリ（frozen, extra="allow"） |
| `AuditLogBatch` | Pydantic Model | バッチ処理用コンテナ |
| `DANGEROUS_ACTIONS` | frozenset | 危険アクションの定義 |

**loader.py**:
| 関数 | 説明 |
|------|------|
| `load_audit_log()` | Eager読み込み（Polars/Pandas） |
| `load_audit_log_lazy()` | 遅延評価（DuckDB/Polars LazyFrame） |
| `stream_audit_log()` | バッチストリーミング |
| `stream_audit_log_mmap()` | メモリマップ高速ストリーミング |
| `create_duckdb_table()` | DuckDBテーブル作成 |
| `query_duckdb()` | DuckDBクエリ実行 |

**analyzers/**:
| クラス | 説明 |
|--------|------|
| `BaseAnalyzer[DF]` | 抽象基底クラス（ジェネリック） |
| `AnomalyDetector` | 異常検出（危険アクション/時間外/バルク） |
| `TimeSeriesAnalyzer` | 時系列パターン分析 |
| `UserActivityAnalyzer` | ユーザー別分析 |

**utils/constants.py**:
| 定数 | 説明 |
|------|------|
| `CRITICAL_ACTIONS` | CRITICALリスクのアクション |
| `HIGH_RISK_ACTIONS` | HIGHリスクのアクション |
| `BUSINESS_HOURS` | 営業時間定義（9-18時） |
| `WEEKEND_DAYS` | 週末（5, 6） |
| `BULK_OPERATION_THRESHOLD` | 一括操作閾値 |
| `KNOWN_BOT_PATTERNS` | Bot判定パターン |
| `ACTION_COLORS` | アクションカテゴリ色 |
| `RISK_COLORS` | リスクレベル色 |

---

### 0.4 notebooks/ の詳細分析

#### 各ノートブックのimport

| ノートブック | import |
|-------------|--------|
| 全ノートブック共通 | `marimo`, `polars`, `json`, `datetime` |
| 分析系（4ファイル） | + `altair` |
| **audit_analyzerへの参照** | **❌ なし** |

#### 実装されている機能（重複）

**index.py**:
- ファイルアップロードUI
- JSON/NDJSONパース（独自実装）
- ナビゲーションカード

**action_tracker.py**:
- アクション種別フィルタリング
- リポジトリ別チャート
- イベントテーブル

**anomaly_detection.py**:
- 危険アクション検出（`DANGEROUS_ACTIONS`を独自定義）
- 営業時間外アクティビティ（ロジック独自実装）
- バルク操作検出（閾値独自定義）

**user_activity.py**:
- ユーザー別アクティビティ
- Top N ユーザーチャート

**time_analysis.py**:
- 時間帯別分布
- 曜日別分布
- 日次トレンド

---

### 0.5 pyproject.toml の設定状況

| 項目 | 状態 |
|------|------|
| パッケージ名 | `audit-analyzer` |
| ビルドバックエンド | `hatchling` |
| ビルド対象 | `src/audit_analyzer` ✅ |
| CLIエントリポイント | `audit-analyzer = "audit_analyzer.cli:main"` ⚠️ **cli.py未実装** |
| 型付き | `py.typed` ✅ |
| テスト設定 | pytest + coverage (80%目標) ✅ |
| リンター | Ruff (厳格設定) ✅ |

---

### 0.6 選択肢の整理

#### Option A: src/を活用する方向にリファクタリング

**メリット**:
- 設計意図通りのアーキテクチャ実現
- コード重複の解消
- テスト済みロジックの再利用
- 型安全性の向上（Pydanticモデル）

**デメリット**:
- notebooks/の大幅な書き換えが必要
- 既存の動作するノートブックを壊すリスク
- 作業工数大

#### Option B: src/を削除してnotebooks/を正とする

**メリット**:
- シンプルな構造
- notebooks/がスタンドアロンで完結
- marimoサンドボックスとの相性が良い
- 作業工数小

**デメリット**:
- テスト済みのコードを捨てることになる
- 型安全性の低下
- 将来の拡張性が低い
- 定数・閾値がノートブック間で不整合になるリスク

#### Option C: 段階的な統合（推奨？）

1. notebooks/は現状維持（動作優先）
2. src/の定数・設定値のみをnotebooks/から参照
3. 将来的にロジックも段階的に移行

**メリット**:
- リスクが低い
- 段階的に改善できる
- 両方の資産を活かせる

**デメリット**:
- 過渡期は2つのコードベースが並存
- 整合性管理が必要

---

### 0.7 決定事項 ✅

**2025-12-29 決定**

| 項目 | 決定内容 |
|------|----------|
| **方針** | **Option B**: src/を削除してnotebooks/を正とする |
| **用途** | notebooks/のみ（CLIやパッケージ配布は不要） |
| **公開方法** | GitHub Pages（marimo export html-wasm） |

---

## 1. リファクタリング作業計画

### 1.1 削除対象

以下のファイル・ディレクトリを削除します：

```
削除対象:
├── src/                    # 全体削除
│   └── audit_analyzer/
│       ├── __init__.py
│       ├── models.py
│       ├── loader.py
│       ├── py.typed
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anomaly.py
│       │   ├── time_series.py
│       │   └── user_activity.py
│       └── utils/
│           ├── __init__.py
│           └── constants.py
│
├── tests/                  # 全体削除（src/のテストのため）
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_loader.py
│   ├── test_analyzers.py
│   └── fixtures/
```

### 1.2 pyproject.toml 修正内容

以下の設定を削除または修正：

| セクション | 変更内容 |
|-----------|----------|
| `[project.scripts]` | 削除（CLIエントリポイント） |
| `[tool.hatch.build.targets.wheel]` | 削除（パッケージビルド不要） |
| `[tool.pytest.*]` | 修正（notebooks/用テストに変更） |
| `[tool.coverage.*]` | 修正または削除 |
| `[tool.ruff.lint.per-file-ignores]` | `src/`関連を削除 |
| `[tool.mypy]` | 修正（src/関連を削除） |

### 1.3 維持するファイル

```
維持:
├── notebooks/              # メインコンテンツ
│   ├── index.py
│   ├── action_tracker.py
│   ├── anomaly_detection.py
│   ├── user_activity.py
│   └── time_analysis.py
│
├── data/                   # テストデータ
│   └── *.json
│
├── docs/                   # ドキュメント
│   ├── DESIGN.md
│   └── copilot/PLAN.md
│
├── .github/                # CI/CD、GitHub設定
│   ├── workflows/
│   ├── copilot-instructions.md
│   └── instructions/
│
├── pyproject.toml          # 依存関係定義（簡素化）
├── README.md               # プロジェクト説明（要更新）
├── LICENSE
└── .pre-commit-config.yaml # pre-commit設定（要修正）
```

### 1.4 更新が必要なファイル

| ファイル | 更新内容 |
|----------|----------|
| `README.md` | アーキテクチャ説明を簡素化、src/への言及を削除 |
| `docs/DESIGN.md` | notebooks/中心のアーキテクチャに更新 |
| `.github/copilot-instructions.md` | src/への言及を削除 |
| `.pre-commit-config.yaml` | pytest関連のフック修正 |
| `pyproject.toml` | 上記1.2の修正 |

---

## 2. 詳細TODO

### Phase 1: src/ と tests/ の削除

- [ ] **Task 1.1**: `src/` ディレクトリを削除
- [ ] **Task 1.2**: `tests/` ディレクトリを削除
- [ ] **Task 1.3**: pyproject.toml から以下を削除
  - [ ] `[project.scripts]` セクション
  - [ ] `[tool.hatch.build.targets.wheel]` セクション
  - [ ] `[tool.ruff]` の `src = ["src", ...]` から "src" を削除
  - [ ] `[tool.ruff.lint.per-file-ignores]` の `"src/**/*.py"` を削除
  - [ ] `[tool.pytest.ini_options]` の `pythonpath = ["src"]` を削除
  - [ ] `[tool.coverage.*]` の `source = ["audit_analyzer"]` を修正
  - [ ] `[tool.mypy]` の `packages = ["audit_analyzer"]` を削除
- [ ] **Task 1.4**: 動作確認（uv sync、pre-commit）

### Phase 2: ドキュメント更新

- [ ] **Task 2.1**: README.md 更新
  - [ ] アーキテクチャ説明をnotebooks/中心に変更
  - [ ] src/への言及を削除
  - [ ] インストール・実行方法の簡素化
- [ ] **Task 2.2**: docs/DESIGN.md 更新
  - [ ] notebooks/スタンドアロン構成に変更
  - [ ] GitHub Pages公開の説明を追加
- [ ] **Task 2.3**: .github/copilot-instructions.md 更新
  - [ ] src/への言及を削除
  - [ ] notebooks/の構成説明を更新

### Phase 3: CI/CD・ツール設定の調整

- [ ] **Task 3.1**: .pre-commit-config.yaml 修正
  - [ ] pytest実行の除外または修正
- [ ] **Task 3.2**: .github/workflows/ の確認・修正
  - [ ] テスト実行ステップの修正または削除
- [ ] **Task 3.3**: Ruff/mypy設定の調整
  - [ ] notebooks/のみを対象に変更

### Phase 4: notebooks/のテスト戦略（将来）

- [ ] **Task 4.1**: marimo export の動作確認テスト
- [ ] **Task 4.2**: notebooks/の構文チェックテスト
- [ ] **Task 4.3**: GitHub Actions でのhtml-wasm生成テスト

---

## 3. marimoノートブックテスト戦略（将来）

> ※ 前セクションの内容をPhase 4以降で実施

### 3.1 テスト対象（notebooks/のみ）

### 1.1 なぜこのテストが必要か

**問題意識**:
- marimoノートブックは実行時エラーが発生しやすい（変数スコープ、表示問題など）
- 手動での動作確認は時間がかかり、リグレッションを見逃しやすい
- CI/CDで自動検証できれば、品質を保ちながら開発速度を上げられる

**期待される効果**:
1. **早期発見**: コミット前に問題を検出
2. **リグレッション防止**: 既存機能が壊れないことを保証
3. **ドキュメント化**: テストがノートブックの期待動作を示す
4. **リファクタリング支援**: 安心してコードを改善できる

### 1.2 対象ノートブック

```
notebooks/
├── index.py                # ナビゲーション画面
├── action_tracker.py       # アクション追跡
├── anomaly_detection.py    # 異常検知
├── user_activity.py        # ユーザー活動分析
└── time_analysis.py        # 時系列分析
```

**特性**:
- インラインスクリプト依存関係（`/// script`）
- marimo固有のリアクティブ実行モデル
- UIコンポーネント（mo.ui.*）の使用
- 外部データファイル依存

---

## 2. 現状分析

### 2.1 既存テストカバレッジ

✅ **カバー済み**:
- `src/audit_analyzer/`: モデル、ローダー、アナライザー
- 単体テスト: 15 passed, 2 skipped
- pre-commitフック: Ruff, Bandit, etc.

❌ **未カバー**:
- `notebooks/`: ノートブックファイル（0%）
- セル間のデータフロー検証
- UI表示の正当性検証
- 大規模データでの動作確認

### 2.2 marimoの実行モデル理解

**重要な特性**:
1. **セルの独立性**: 各セルは独立した関数として実行
2. **リアクティビティ**: 変数変更時に依存セルが自動再実行
3. **表示ルール**: `return`または評価式で結果を表示
4. **サンドボックス**: インライン依存関係で隔離環境作成

**テスト上の考慮点**:
- marimoランタイムなしでセルを実行可能か？
- リアクティブな挙動をどうテストするか？
- UI入力のモック方法は？

---

## 3. テスト戦略

### 3.1 レイヤー別アプローチ

#### **Level 0: Static Analysis（静的解析）** 🟢
- **目的**: 構文エラー、型エラーの早期発見
- **ツール**: AST解析、Ruff、mypy/Pylance
- **コスト**: 低（数秒）
- **カバレッジ**: 構文、インポート、型

#### **Level 1: Syntax & Import Test（構文・インポートテスト）** 🟢
- **目的**: ノートブックがPythonモジュールとして読み込めるか
- **手法**: `importlib`でモジュールインポート
- **コスト**: 低（数秒）
- **カバレッジ**: インポートエラー、依存関係不足

#### **Level 2: App Instantiation Test（アプリ生成テスト）** 🟡
- **目的**: marimoアプリケーションオブジェクトが生成できるか
- **手法**: `marimo.App`を直接インスタンス化
- **コスト**: 中（10秒程度）
- **カバレッジ**: セル定義、アプリ構造

#### **Level 3: Cell Execution Test（セル実行テスト）** 🟡
- **目的**: 各セルが実際に実行できるか
- **手法**: セル関数を直接呼び出し
- **コスト**: 中（30秒程度）
- **カバレッジ**: セルロジック、データフロー

#### **Level 4: Integration Test（統合テスト）** 🔴
- **目的**: 実データで end-to-end 動作検証
- **手法**: marimo serverを起動して実行
- **コスト**: 高（分単位）
- **カバレッジ**: 全体の動作、パフォーマンス

#### **Level 5: Visual Regression Test（ビジュアルリグレッションテスト）** 🔴
- **目的**: UI表示の変化を検出
- **手法**: Playwright + スクリーンショット比較
- **コスト**: 非常に高（分単位）
- **カバレッジ**: UI表示、チャート描画

**優先順位**: Level 0 → 1 → 2 → 3 → (4, 5は将来的に検討)

---

## 4. 技術的検討事項

### 4.1 marimoノートブックの読み込み方法

**Option A: 直接import** 🟢
```python
import importlib.util
spec = importlib.util.spec_from_file_location("notebook", "notebooks/index.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app  # marimo.App
```

**メリット**:
- シンプル、高速
- marimoランタイム不要

**デメリット**:
- インライン依存関係が解決されない可能性
- リアクティブな挙動は再現できない

---

**Option B: marimo CLI経由** 🟡
```python
subprocess.run(["marimo", "run", "notebook.py", "--headless"])
```

**メリット**:
- 本番環境に近い
- 完全な機能テスト

**デメリット**:
- 遅い
- CI環境で不安定な可能性

---

**Option C: marimo API（もしあれば）** 🔴
```python
from marimo import api
app = api.load_notebook("notebook.py")
results = app.run()
```

**メリット**:
- プログラマティック制御
- テストに最適

**デメリット**:
- marimoにそのようなAPIが存在するか不明
- 調査が必要

**推奨**: まずOption Aで実装、必要に応じてOption Bを追加

### 4.2 テストデータの準備

**既存のフィクスチャ活用**:
```python
# tests/conftest.py
@pytest.fixture
def sample_audit_entries() -> list[dict[str, Any]]:
    """既存のテストデータ"""
```

**ノートブック用フィクスチャ追加**:
```python
@pytest.fixture
def notebook_test_data(tmp_path: Path) -> Path:
    """ノートブック用のJSONファイル生成"""
    data_file = tmp_path / "test_audit.json"
    # 100件程度の小規模データ
    data_file.write_text(json.dumps([...]))
    return data_file
```

**データサイズ**:
- 単体テスト: 10-100件（秒単位）
- 統合テスト: 1,000-10,000件（分単位）
- パフォーマンステスト: 100,000件以上（将来的に）

### 4.3 UI要素のモック

**課題**: `mo.ui.file()`, `mo.ui.slider()` などの入力要素

**戦略**:
1. **モック不要のテスト**: 初期状態（入力なし）で実行
2. **値の注入**: セル関数に直接引数を渡す
3. **モックオブジェクト**: `unittest.mock.Mock`で代替

**例**:
```python
# モック不要パターン
def test_index_without_file(index_module):
    """ファイル未選択時にエラーが出ないこと"""
    # file_input.value is None の状態でテスト

# モック使用パターン
def test_action_tracker_with_data(action_tracker_module):
    mock_df = pl.DataFrame({"action": ["repo.create"]})
    # mock_df をセルに注入してテスト
```

---

## 5. 詳細TODO

### 🎯 Phase 1: 基盤構築（Level 0-1）

#### Task 1.1: テストファイル作成
- [ ] `tests/test_notebooks_syntax.py` 作成
  - [ ] 全ノートブックファイルをパラメトライズ
  - [ ] `ast.parse()` で構文チェック
  - [ ] 期待される構造（`app`, `@app.cell`）が存在するか確認
- [ ] 実装時間: 30分
- [ ] 依存: なし

#### Task 1.2: インポートテスト実装
- [ ] `test_notebooks_can_be_imported()` 実装
  - [ ] `importlib` でモジュールロード
  - [ ] `ImportError` が発生しないことを確認
  - [ ] `app` オブジェクトが存在することを確認
- [ ] 実装時間: 30分
- [ ] 依存: Task 1.1

#### Task 1.3: アプリ構造検証
- [ ] `test_app_structure()` 実装
  - [ ] `app` が `marimo.App` のインスタンスであることを確認
  - [ ] セル数が期待値と一致するか確認
  - [ ] `app._cell_manager` または内部構造を調査
- [ ] 実装時間: 1時間
- [ ] 依存: Task 1.2, marimoの内部API調査

#### Task 1.4: CI統合
- [ ] `.github/workflows/test.yml` に追加
  - [ ] `pytest tests/test_notebooks_syntax.py`
  - [ ] ノートブック変更時にトリガー
- [ ] 実装時間: 15分
- [ ] 依存: Task 1.1-1.3

**Phase 1 完了条件**:
- ✅ 全ノートブックが構文エラーなし
- ✅ 全ノートブックがインポート可能
- ✅ CIで自動実行される

---

### 🎯 Phase 2: セル実行テスト（Level 2-3）

#### Task 2.1: テストフィクスチャ拡張
- [ ] `conftest.py` に `notebook_test_data` フィクスチャ追加
  - [ ] 小規模テストデータ（100件）をJSON生成
  - [ ] 各アクションタイプを網羅
  - [ ] 異常データ（null値、範囲外）を含む
- [ ] 実装時間: 30分
- [ ] 依存: 既存の `conftest.py`

#### Task 2.2: セル実行フレームワーク構築
- [ ] `tests/test_notebooks_execution.py` 作成
- [ ] セル実行ヘルパー関数 `execute_cell()` 実装
  - [ ] セル間の依存関係を解決
  - [ ] グローバル名前空間を管理
  - [ ] 例外をキャッチして詳細ログ出力
- [ ] 実装時間: 2時間
- [ ] 依存: Task 2.1, marimoのセル実行モデル理解

#### Task 2.3: index.pyのテスト
- [ ] `test_index_cells_execute()` 実装
  - [ ] 各セルが例外なく実行できることを確認
  - [ ] `mo.md()` の戻り値が `marimo.Html` 型であることを確認
  - [ ] ナビゲーションカードが5つ生成されることを確認
- [ ] 実装時間: 1時間
- [ ] 依存: Task 2.2

#### Task 2.4: action_tracker.pyのテスト
- [ ] `test_action_tracker_with_data()` 実装
  - [ ] テストデータでフィルタリング動作を確認
  - [ ] チャート生成が成功することを確認
  - [ ] テーブル表示が正しいデータを含むことを確認
- [ ] 実装時間: 1時間
- [ ] 依存: Task 2.2, 2.3

#### Task 2.5: anomaly_detection.pyのテスト
- [ ] `test_anomaly_detection_cells()` 実装
  - [ ] 危険なアクション検出ロジックを検証
  - [ ] 営業時間外アクティビティ検出を検証
  - [ ] バルク操作検出を検証
- [ ] 実装時間: 1.5時間
- [ ] 依存: Task 2.2, 2.3

#### Task 2.6: user_activity.pyとtime_analysis.pyのテスト
- [ ] `test_user_activity_cells()` 実装
- [ ] `test_time_analysis_cells()` 実装
- [ ] 実装時間: 各1時間
- [ ] 依存: Task 2.2, 2.3

#### Task 2.7: エラーハンドリングテスト
- [ ] 無効なデータでの挙動を確認
  - [ ] 空ファイル
  - [ ] 不正なJSON
  - [ ] 必須フィールド欠落
- [ ] 実装時間: 1時間
- [ ] 依存: Task 2.2-2.6

**Phase 2 完了条件**:
- ✅ 全ノートブックのセルが実行可能
- ✅ テストデータで正常に動作
- ✅ エラーケースでもクラッシュしない

---

### 🎯 Phase 3: 品質向上とドキュメント

#### Task 3.1: カバレッジ測定
- [ ] `pytest-cov` で `notebooks/` のカバレッジを計測
- [ ] 目標: 80%以上
- [ ] 実装時間: 30分
- [ ] 依存: Phase 2完了

#### Task 3.2: テストドキュメント作成
- [ ] `docs/testing/notebook-testing.md` 作成
  - [ ] テスト戦略の説明
  - [ ] ローカルでのテスト実行方法
  - [ ] トラブルシューティング
- [ ] 実装時間: 1時間
- [ ] 依存: Phase 2完了

#### Task 3.3: pre-commitフック追加
- [ ] `.pre-commit-config.yaml` に追加
  - [ ] `pytest tests/test_notebooks_syntax.py` を実行
  - [ ] 軽量テストのみ（数秒以内）
- [ ] 実装時間: 15分
- [ ] 依存: Phase 1完了

#### Task 3.4: README更新
- [ ] `README.md` にテスト情報を追加
  - [ ] バッジ追加（テストカバレッジ）
  - [ ] テスト実行方法
- [ ] 実装時間: 30分
- [ ] 依存: Task 3.1-3.3

**Phase 3 完了条件**:
- ✅ ドキュメントが充実
- ✅ 開発者が簡単にテストを実行・追加できる

---

### 🔮 Phase 4: 将来的な拡張（オプション）

#### Task 4.1: 統合テスト（Level 4）
- [ ] marimo serverを起動してE2Eテスト
- [ ] `playwright` または `selenium` で実際のブラウザ操作
- [ ] 実装時間: 4時間以上
- [ ] 依存: Phase 3完了

#### Task 4.2: パフォーマンステスト
- [ ] 大規模データ（100万件）での動作確認
- [ ] メモリ使用量、実行時間の計測
- [ ] ベンチマーク結果の記録
- [ ] 実装時間: 3時間以上
- [ ] 依存: Phase 3完了

#### Task 4.3: ビジュアルリグレッションテスト（Level 5）
- [ ] `playwright` でスクリーンショット取得
- [ ] `pixelmatch` で画像比較
- [ ] ベースライン画像の管理
- [ ] 実装時間: 5時間以上
- [ ] 依存: Task 4.1

**Phase 4 完了条件**:
- ✅ 本番環境に近い状態でのテスト
- ✅ パフォーマンスリグレッション検出

---

## 6. リスクと課題

### 6.1 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| marimoの内部APIが不安定 | 高 | 中 | 公式ドキュメント調査、コミュニティに質問 |
| セル間依存関係の解決が困難 | 中 | 高 | セル実行順序を手動で管理 |
| UI要素のモックが複雑 | 低 | 中 | UI不要のロジックテストに集中 |
| テスト実行時間が長くなる | 中 | 中 | Level 0-1のみpre-commitに含める |
| CIでのmarimo環境構築失敗 | 高 | 低 | Dockerコンテナで環境統一 |

### 6.2 プロジェクト管理上のリスク

- **スコープクリープ**: Phase 4まで実装すると工数過大
  - **対策**: Phase 1-2を優先、Phase 3-4は必要に応じて
- **既存機能への影響**: テスト追加で開発速度低下
  - **対策**: 軽量なテストから開始、段階的に拡充

---

## 7. 進捗状況

### 7.1 タイムライン

```
Phase 1 (基盤構築)    ████░░░░░░  40% 🟡
├─ Task 1.1           ░░░░░░░░░░   0%
├─ Task 1.2           ░░░░░░░░░░   0%
├─ Task 1.3           ░░░░░░░░░░   0%
└─ Task 1.4           ░░░░░░░░░░   0%

Phase 2 (セル実行)    ░░░░░░░░░░   0% ⚪
Phase 3 (品質向上)    ░░░░░░░░░░   0% ⚪
Phase 4 (拡張)        ░░░░░░░░░░   0% ⚪
```

### 7.2 完了したタスク

- ✅ **2025-12-29**: PLAN.md作成（このドキュメント）

### 7.3 次のアクション

1. **調査フェーズ** (優先度: 最高)
   - [ ] marimoのApp構造を調査
   - [ ] セルの実行方法を調査
   - [ ] 既存のテストパターンを分析

2. **意思決定** (優先度: 高)
   - [ ] どのレベルまで実装するか決定
   - [ ] テスト実行時間の目標を設定
   - [ ] CI/CDへの統合方針を決定

3. **実装開始** (優先度: 中)
   - [ ] Phase 1 Task 1.1から着手

---

## 8. 参考資料

### 8.1 marimoドキュメント

- [marimo Documentation](https://docs.marimo.io/)
- [Testing Strategies (要調査)](https://docs.marimo.io/testing/)
- [API Reference (要調査)](https://docs.marimo.io/api/)

### 8.2 関連Issue・PR

- (今後追加予定)

### 8.3 類似プロジェクト

- Jupyter Notebook Testing: `nbval`, `testbook`
- Observable Testing: (要調査)

---

## 9. 議論ポイント

### 🤔 検討が必要な事項

1. **テスト粒度**: どこまで細かくテストするか？
   - セル単位？
   - ノートブック単位？
   - 出力の型チェックまで？

2. **CI実行時間**: 許容できる実行時間は？
   - 1分以内？
   - 5分以内？
   - 10分以内？

3. **テストデータ**: どのように管理するか？
   - Git管理？
   - オンデマンド生成？
   - 実データのサンプル？

4. **失敗時の対応**: テストが失敗したらどうするか？
   - コミットブロック？
   - 警告のみ？
   - マージブロック？

5. **Phase 4の必要性**: 統合テストは本当に必要か？
   - 手動テストで代替可能？
   - 投資対効果は？

---

## 10. 更新履歴

| 日付 | 変更内容 | 担当 |
|------|---------|------|
| 2025-12-29 | 初版作成 | GitHub Copilot |

---

**次の更新**: Task実行時または週次レビュー時
