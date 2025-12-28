# GitHub Copilot Instructions

このドキュメントは、GitHub Copilotがこのプロジェクトのコンテキストを理解し、
適切なコード提案を行うための指示を定義します。

## プロジェクト概要

**GitHub Organization Audit Log Analyzer** - 監査ログ分析ツール

- **言語**: Python 3.12+
- **パッケージマネージャー**: uv
- **ノートブック**: marimo
- **データ処理**: DuckDB, Polars
- **バリデーション**: Pydantic v2

## アーキテクチャ

```
src/audit_analyzer/    # コアライブラリ（再利用可能なロジック）
├── models.py          # Pydanticデータモデル
├── loader.py          # データローダー
└── analyzers/         # 分析エンジン

notebooks/             # marimo UI（ビジュアル分析）
```

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
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# 2. サードパーティ
import polars as pl
from pydantic import BaseModel

# 3. ローカル
from audit_analyzer.models import AuditLogEntry
```

### 型ヒント

- **必須**: すべての関数・メソッドに型ヒントを付与
- **`from __future__ import annotations`**: ファイル先頭で必ずインポート
- **Union**: `X | None` 形式を使用（`Optional[X]` は使わない）
- **コレクション**: `list[str]`, `dict[str, int]` 形式を使用

```python
from __future__ import annotations

def process_entries(
    entries: list[AuditLogEntry],
    *,
    limit: int | None = None,
) -> pl.DataFrame:
    """監査ログエントリを処理してDataFrameに変換する。"""
    ...
```

### ドキュメント文字列

- **形式**: Google Style
- **言語**: 日本語（公開API）または英語（内部実装）

```python
def load_audit_log(path: str | Path) -> pl.DataFrame:
    """監査ログファイルを読み込む。

    Args:
        path: JSONまたはNDJSONファイルへのパス

    Returns:
        監査ログエントリを含むPolars DataFrame

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: サポートされていないフォーマットの場合
    """
```

## Pydanticモデルの書き方

### 基本パターン

```python
from pydantic import BaseModel, ConfigDict, Field

class AuditLogEntry(BaseModel):
    """監査ログエントリモデル。"""

    model_config = ConfigDict(
        frozen=True,           # イミュータブル
        extra="allow",         # 未知フィールドを許容
        populate_by_name=True, # エイリアスでもアクセス可能
    )

    timestamp: datetime = Field(description="イベント発生時刻")
    action: str = Field(description="実行されたアクション")
    actor: str | None = Field(default=None, description="実行者")
```

### バリデーション

```python
from pydantic import field_validator, model_validator

class Config(BaseModel):
    threshold: int = Field(ge=0, le=100)

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        if v < 10:
            raise ValueError("閾値は10以上である必要があります")
        return v
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
    return mo, pl


@app.cell
def _(mo):
    mo.md(r"""
    # タイトル

    説明テキスト
    """)
    return


@app.cell
def _(mo, pl):
    # インタラクティブなUI要素
    file_input = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        label="監査ログファイルを選択",
    )
    file_input
    return (file_input,)
```

### セル間のデータ受け渡し

```python
@app.cell
def _(file_input, pl):
    # 前のセルで定義した file_input を参照
    if file_input.value:
        df = pl.read_json(file_input.value[0].contents)
    else:
        df = pl.DataFrame()
    return (df,)


@app.cell
def _(df, mo):
    # df を使用
    mo.ui.table(df)
    return
```

### UI要素のベストプラクティス

```python
# ✅ Good: 説明的なラベル
slider = mo.ui.slider(1, 100, value=10, label="表示件数")

# ❌ Bad: ラベルなし
slider = mo.ui.slider(1, 100, value=10)

# ✅ Good: リアクティブな条件分岐
mo.stop(not file_input.value, mo.md("ファイルを選択してください"))

# ❌ Bad: 通常のif文で早期リターン
if not file_input.value:
    return
```

## DuckDB/Polarsクエリ

### DuckDBパターン

```python
import duckdb

# ファイルから直接クエリ
result = duckdb.sql("""
    SELECT
        actor,
        action,
        COUNT(*) as count
    FROM read_json_auto('data/audit_log.json')
    WHERE timestamp >= '2024-01-01'
    GROUP BY actor, action
    ORDER BY count DESC
    LIMIT 10
""").pl()  # Polars DataFrameに変換
```

### Polars遅延評価パターン

```python
import polars as pl

# LazyFrameで効率的な処理
df = (
    pl.scan_ndjson("data/audit_log.ndjson")
    .filter(pl.col("timestamp") >= datetime(2024, 1, 1))
    .group_by("actor", "action")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .limit(10)
    .collect()  # ここで実行
)
```

## テストの書き方

### 基本パターン

```python
import pytest
from audit_analyzer.models import AuditLogEntry


class TestAuditLogEntry:
    """AuditLogEntryモデルのテスト。"""

    def test_valid_entry(self, sample_entry: dict) -> None:
        """有効なエントリをパースできること。"""
        entry = AuditLogEntry.model_validate(sample_entry)
        assert entry.action == sample_entry["action"]

    def test_missing_required_field(self) -> None:
        """必須フィールドがない場合にエラーになること。"""
        with pytest.raises(ValueError):
            AuditLogEntry.model_validate({})

    @pytest.mark.parametrize(
        "action",
        ["repo.create", "repo.destroy", "org.add_member"],
    )
    def test_various_actions(self, action: str) -> None:
        """様々なアクションタイプをパースできること。"""
        entry = AuditLogEntry.model_validate({
            "timestamp": "2024-01-01T00:00:00Z",
            "action": action,
        })
        assert entry.action == action
```

### フィクスチャ（conftest.py）

```python
import pytest
from pathlib import Path


@pytest.fixture
def sample_entry() -> dict:
    """サンプルの監査ログエントリ。"""
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "action": "repo.create",
        "actor": "test-user",
        "repo": "org/repo",
    }


@pytest.fixture
def sample_log_file(tmp_path: Path) -> Path:
    """一時的なログファイル。"""
    file_path = tmp_path / "test.json"
    file_path.write_text('[{"timestamp": "2024-01-01T00:00:00Z", "action": "test"}]')
    return file_path
```

## 禁止事項

- ❌ `print()` デバッグ（`logging` または `mo.md()` を使用）
- ❌ グローバル変数の変更
- ❌ `Any` 型の乱用
- ❌ 裸の `except:` 句
- ❌ `# type: ignore` の無条件使用
- ❌ 本番データのハードコード

## よく使うパターン

### エラーハンドリング

```python
from audit_analyzer.models import AuditLogEntry
from pydantic import ValidationError

def parse_safe(data: dict) -> AuditLogEntry | None:
    """バリデーションエラーを握りつぶして None を返す。"""
    try:
        return AuditLogEntry.model_validate(data)
    except ValidationError:
        return None
```

### 設定の読み込み

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    data_dir: Path = Path("data")
    max_entries: int = 10000

    model_config = {"env_prefix": "AUDIT_"}
```

## 参考リンク

- [marimo Documentation](https://docs.marimo.io/)
- [Polars User Guide](https://docs.pola.rs/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
