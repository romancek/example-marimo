# Pydantic モデルの追加

このプロンプトを使用して、新しいPydanticモデルを追加してください。

## 入力情報

作成するモデルについて以下を指定してください：

- **モデル名**: {{model_name}}
- **目的**: {{purpose}}
- **フィールド**: {{fields}}
- **バリデーション要件**: {{validation_rules}}

## テンプレート

### 基本モデル

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class {{model_name}}(BaseModel):
    """{{purpose}}

    Attributes:
        {{fields_doc}}

    Example:
        >>> entry = {{model_name}}.model_validate({
        ...     "field1": "value1",
        ...     "field2": 42,
        ... })
        >>> entry.field1
        'value1'
    """

    model_config = ConfigDict(
        # イミュータブル（変更不可）
        frozen=True,
        # 未知のフィールドを許容（GitHub APIの拡張に対応）
        extra="allow",
        # エイリアスでも属性名でもアクセス可能
        populate_by_name=True,
        # シリアライズ時にエイリアスを使用
        serialize_by_alias=True,
        # バリデーションエラーに入力値を含める
        validate_default=True,
    )

    # === 必須フィールド ===
    # field1: str = Field(description="フィールド1の説明")

    # === オプショナルフィールド ===
    # field2: int | None = Field(default=None, description="フィールド2の説明")

    # === 計算プロパティ ===
    # @property
    # def derived_value(self) -> str:
    #     """導出値を返す。"""
    #     return f"{self.field1}_{self.field2}"
```

### フィールドバリデーション

```python
from pydantic import field_validator, ValidationInfo


class {{model_name}}(BaseModel):
    # フィールド定義...

    @field_validator("field_name", mode="before")
    @classmethod
    def validate_field_name(cls, v: Any) -> str:
        """フィールドのバリデーション。

        Args:
            v: 入力値

        Returns:
            バリデーション済みの値

        Raises:
            ValueError: バリデーションエラー
        """
        if v is None:
            return "default_value"
        if isinstance(v, str):
            return v.strip().lower()
        raise ValueError(f"期待: str, 実際: {type(v)}")

    @field_validator("numeric_field")
    @classmethod
    def validate_numeric_range(cls, v: int) -> int:
        """数値範囲のバリデーション。"""
        if not (0 <= v <= 100):
            raise ValueError("値は0-100の範囲である必要があります")
        return v
```

### モデルレベルバリデーション

```python
from pydantic import model_validator


class {{model_name}}(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        """日付範囲の整合性を検証。"""
        if self.end_date < self.start_date:
            raise ValueError("end_dateはstart_date以降である必要があります")
        return self
```

### Enum / Literal 型

```python
from enum import StrEnum
from typing import Literal


class ActionCategory(StrEnum):
    """アクションカテゴリ。"""

    REPOSITORY = "repository"
    ORGANIZATION = "organization"
    SECURITY = "security"


class {{model_name}}(BaseModel):
    # Enum型
    category: ActionCategory = Field(description="アクションカテゴリ")

    # Literal型（値を制限）
    status: Literal["active", "inactive", "pending"] = Field(
        default="pending",
        description="ステータス",
    )
```

### 日付/時刻フィールド

```python
from datetime import datetime
from pydantic import AliasChoices


class {{model_name}}(BaseModel):
    # 複数のエイリアスをサポート
    timestamp: Annotated[
        datetime,
        Field(
            validation_alias=AliasChoices(
                "@timestamp",  # GitHub API形式
                "timestamp",   # 標準形式
                "created_at",  # 別名
            ),
            description="イベント発生時刻",
        ),
    ]

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """様々な形式の日時文字列をパース。"""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # ISO 8601形式
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, (int, float)):
            # Unixタイムスタンプ
            return datetime.fromtimestamp(v)
        raise ValueError(f"日時形式が不正: {v}")
```

## テストテンプレート

```python
import pytest
from audit_analyzer.models import {{model_name}}


class Test{{model_name}}:
    """{{model_name}}のテスト。"""

    @pytest.fixture
    def valid_data(self) -> dict:
        """有効なテストデータ。"""
        return {
            "field1": "value1",
            "field2": 42,
        }

    def test_valid_model(self, valid_data: dict) -> None:
        """有効なデータでモデルを作成できること。"""
        model = {{model_name}}.model_validate(valid_data)
        assert model.field1 == "value1"
        assert model.field2 == 42

    def test_immutable(self, valid_data: dict) -> None:
        """モデルがイミュータブルであること。"""
        model = {{model_name}}.model_validate(valid_data)
        with pytest.raises(Exception):  # ValidationError
            model.field1 = "new_value"

    def test_extra_fields_allowed(self, valid_data: dict) -> None:
        """未知のフィールドが許容されること。"""
        data = {**valid_data, "unknown_field": "unknown_value"}
        model = {{model_name}}.model_validate(data)
        assert model.model_extra["unknown_field"] == "unknown_value"

    @pytest.mark.parametrize(
        "field,value,expected_error",
        [
            ("field1", None, "Input should be a valid string"),
            ("field2", "not_a_number", "Input should be a valid integer"),
        ],
    )
    def test_validation_errors(
        self,
        valid_data: dict,
        field: str,
        value: Any,
        expected_error: str,
    ) -> None:
        """バリデーションエラーのテスト。"""
        data = {**valid_data, field: value}
        with pytest.raises(ValueError, match=expected_error):
            {{model_name}}.model_validate(data)

    def test_serialization(self, valid_data: dict) -> None:
        """シリアライズが正しく動作すること。"""
        model = {{model_name}}.model_validate(valid_data)
        serialized = model.model_dump()
        assert serialized["field1"] == "value1"

    def test_json_serialization(self, valid_data: dict) -> None:
        """JSON形式でシリアライズできること。"""
        model = {{model_name}}.model_validate(valid_data)
        json_str = model.model_dump_json()
        assert '"field1":"value1"' in json_str
```

## チェックリスト

生成後、以下を確認してください：

- [ ] `model_config` が適切に設定されている
- [ ] すべてのフィールドに `Field(description=...)` がある
- [ ] 必要なバリデーターが実装されている
- [ ] docstringにExampleが含まれている
- [ ] 対応するテストが作成されている
- [ ] `from __future__ import annotations` がある

## 配置場所

- **モデル**: `src/audit_analyzer/models.py`
- **テスト**: `tests/test_models.py`
