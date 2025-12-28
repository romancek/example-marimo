# テストケースの生成

このプロンプトを使用して、既存のコードに対するテストケースを生成してください。

## 入力情報

テスト対象について以下を指定してください：

- **テスト対象モジュール**: {{module_path}}
- **テスト対象クラス/関数**: {{target_name}}
- **重点テスト項目**: {{focus_areas}}

## テスト構造テンプレート

### 基本テストファイル構造

```python
"""{{module_path}}のテスト。

このモジュールでは以下をテストします：
- {{test_item_1}}
- {{test_item_2}}
- {{test_item_3}}
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# テスト対象のインポート
from audit_analyzer.{{module}} import {{target_name}}


class Test{{target_name}}:
    """{{target_name}}のテスト。"""

    # === フィクスチャ ===

    @pytest.fixture
    def sample_data(self) -> dict:
        """テスト用サンプルデータ。"""
        return {
            "key": "value",
        }

    # === 正常系テスト ===

    def test_basic_functionality(self, sample_data: dict) -> None:
        """基本的な機能が動作すること。"""
        result = {{target_name}}(sample_data)
        assert result is not None

    # === 異常系テスト ===

    def test_invalid_input_raises_error(self) -> None:
        """不正な入力でエラーが発生すること。"""
        with pytest.raises(ValueError, match="expected error message"):
            {{target_name}}(invalid_data)

    # === エッジケース ===

    def test_empty_input(self) -> None:
        """空の入力を処理できること。"""
        result = {{target_name}}({})
        assert result == expected_empty_result

    def test_large_input(self) -> None:
        """大量のデータを処理できること。"""
        large_data = generate_large_data(10000)
        result = {{target_name}}(large_data)
        assert len(result) == 10000
```

### パラメータ化テスト

```python
class TestParameterized:
    """パラメータ化テスト。"""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("valid_input_1", "expected_output_1"),
            ("valid_input_2", "expected_output_2"),
            ("edge_case", "edge_result"),
        ],
        ids=["normal_case_1", "normal_case_2", "edge_case"],
    )
    def test_various_inputs(
        self,
        input_value: str,
        expected: str,
    ) -> None:
        """様々な入力に対して正しい出力を返すこと。"""
        result = process(input_value)
        assert result == expected

    @pytest.mark.parametrize(
        "invalid_input,error_type,error_match",
        [
            (None, TypeError, "NoneType"),
            ("", ValueError, "empty"),
            (-1, ValueError, "negative"),
        ],
    )
    def test_invalid_inputs(
        self,
        invalid_input: Any,
        error_type: type[Exception],
        error_match: str,
    ) -> None:
        """不正な入力で適切なエラーが発生すること。"""
        with pytest.raises(error_type, match=error_match):
            process(invalid_input)
```

### 非同期テスト

```python
import pytest


@pytest.mark.asyncio
async def test_async_function() -> None:
    """非同期関数のテスト。"""
    result = await async_function()
    assert result == expected
```

### モック/スタブの使用

```python
from unittest.mock import MagicMock, patch


class TestWithMock:
    """モックを使用したテスト。"""

    def test_with_mock(self) -> None:
        """外部依存をモックしてテスト。"""
        mock_client = MagicMock()
        mock_client.fetch.return_value = {"data": "mocked"}

        result = function_under_test(client=mock_client)

        mock_client.fetch.assert_called_once()
        assert result == expected

    @patch("audit_analyzer.loader.Path.exists")
    def test_with_patch(self, mock_exists: MagicMock) -> None:
        """パッチでファイル存在チェックをモック。"""
        mock_exists.return_value = True

        result = load_file("fake_path.json")

        assert result is not None
```

### Hypothesisによるプロパティベーステスト

```python
from hypothesis import given, strategies as st


class TestPropertyBased:
    """プロパティベーステスト。"""

    @given(st.text(min_size=1))
    def test_non_empty_string_property(self, s: str) -> None:
        """任意の非空文字列で動作すること。"""
        result = process_string(s)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(
        st.integers(min_value=0, max_value=1000),
        st.integers(min_value=0, max_value=1000),
    )
    def test_commutative_property(self, a: int, b: int) -> None:
        """交換法則が成り立つこと。"""
        assert add(a, b) == add(b, a)
```

### polyfactoryによるテストデータ生成

```python
from polyfactory.factories.pydantic_factory import ModelFactory
from audit_analyzer.models import AuditLogEntry


class AuditLogEntryFactory(ModelFactory):
    """AuditLogEntryのファクトリ。"""

    __model__ = AuditLogEntry


class TestWithFactory:
    """ファクトリを使用したテスト。"""

    def test_with_generated_data(self) -> None:
        """生成されたデータでテスト。"""
        entry = AuditLogEntryFactory.build()
        assert entry.timestamp is not None
        assert entry.action is not None

    def test_batch_processing(self) -> None:
        """複数エントリの処理テスト。"""
        entries = AuditLogEntryFactory.batch(100)
        result = process_entries(entries)
        assert len(result) == 100
```

## conftest.py共通フィクスチャ

```python
# tests/conftest.py
"""pytest共通設定・フィクスチャ。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """フィクスチャディレクトリへのパス。"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_audit_log(fixtures_dir: Path) -> list[dict]:
    """サンプル監査ログデータ。"""
    file_path = fixtures_dir / "sample_audit_log.json"
    with file_path.open() as f:
        return json.load(f)


@pytest.fixture
def tmp_json_file(tmp_path: Path) -> Generator[Path, None, None]:
    """一時JSONファイル。"""
    file_path = tmp_path / "test.json"
    yield file_path
    if file_path.exists():
        file_path.unlink()
```

## チェックリスト

テスト生成後、以下を確認してください：

- [ ] 正常系・異常系・エッジケースがカバーされている
- [ ] テストメソッド名が動作を説明している（日本語docstring付き）
- [ ] フィクスチャが適切に使用されている
- [ ] パラメータ化テストで重複を避けている
- [ ] モックが必要最小限に抑えられている
- [ ] 型ヒントが付いている

## テスト実行コマンド

```bash
# 全テスト実行
uv run pytest

# 特定ファイルのみ
uv run pytest tests/test_{{module}}.py

# 特定テストクラスのみ
uv run pytest tests/test_{{module}}.py::Test{{target_name}}

# 特定テストメソッドのみ
uv run pytest tests/test_{{module}}.py::Test{{target_name}}::test_basic_functionality

# カバレッジ付き
uv run pytest --cov=audit_analyzer --cov-report=html

# 詳細出力
uv run pytest -v --tb=short
```
