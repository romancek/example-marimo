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

### 1.2 技術スタック

| コンポーネント | 選定理由 |
|-------------|---------|
| **Pydantic v2** | 高速なバリデーション、TypedDictよりも強力な型付け |
| **DuckDB** | SQLによる集計・分析、メモリ効率の良い列指向処理 |
| **Polars** | Rust製の高速DataFrame、遅延評価サポート |
| **orjson** | 最速のJSONパーサー（標準jsonの5-10倍高速） |

---

## 2. データモデル設計

### 2.1 設計原則

```
┌─────────────────────────────────────────────────────────────┐
│                    AuditLogEntry                            │
├─────────────────────────────────────────────────────────────┤
│ - 不変（frozen=True）: イベントは変更されない               │
│ - 拡張可能（extra="allow"）: 未知のフィールドも保持        │
│ - 型安全: Enumとリテラル型による制約                        │
│ - シリアライズ対応: alias/serializationでAPI互換性維持      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 主要モデル

#### AuditLogEntry（監査ログエントリ）

```python
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

class AuditLogEntry(BaseModel):
    """GitHub Audit Logエントリ（実際のAPIスキーマに基づく）"""
    
    model_config = ConfigDict(
        frozen=True,         # イミュータブル
        extra="allow",       # 未知フィールドを許容
        populate_by_name=True,  # エイリアスでもフィールド名でもOK
    )
    
    # 必須フィールド
    timestamp: Annotated[
        datetime,
        Field(
            validation_alias=AliasChoices("@timestamp", "timestamp", "created_at"),
            description="イベント発生時刻"
        )
    ]
    action: str = Field(description="実行されたアクション")
    
    # アクター情報（オプション）
    actor: str | None = Field(default=None, description="実行者のユーザー名")
    actor_id: int | None = Field(default=None, description="実行者のユーザーID")
    actor_ip: str | None = Field(default=None, description="実行者のIPアドレス")
    
    # 組織情報
    org: str | None = Field(default=None, description="組織名")
    org_id: int | None = Field(default=None, description="組織ID")
    
    # リポジトリ情報
    repo: str | None = Field(default=None, description="リポジトリ名（org/repo形式）")
    repo_id: int | None = Field(default=None, description="リポジトリID")
    
    # 追加メタデータ
    user_agent: str | None = Field(default=None, description="User-Agent")
    document_id: str | None = Field(default=None, alias="_document_id")
```

#### AuditLogAction（アクション列挙型）

```python
from enum import StrEnum

class AuditLogAction(StrEnum):
    """GitHub Audit Logの主要アクション（500+アクションから抜粋）"""
    
    # === Git操作 ===
    GIT_CLONE = "git.clone"
    GIT_PUSH = "git.push"
    GIT_FETCH = "git.fetch"
    
    # === リポジトリ操作 ===
    REPO_CREATE = "repo.create"
    REPO_DESTROY = "repo.destroy"
    REPO_ACCESS = "repo.access"  # 可視性変更
    REPO_RENAME = "repo.rename"
    
    # === 組織管理（危険） ===
    ORG_ADD_MEMBER = "org.add_member"
    ORG_REMOVE_MEMBER = "org.remove_member"
    ORG_UPDATE_MEMBER = "org.update_member"
    ORG_INVITE_MEMBER = "org.invite_member"
    
    # === セキュリティ関連 ===
    SECRET_SCANNING_ALERT_CREATE = "secret_scanning_alert.create"
    SECRET_SCANNING_PUSH_PROTECTION_BYPASS = "secret_scanning_push_protection.bypass"
```

### 2.3 設計根拠

| 設計選択 | 根拠 |
|---------|------|
| `frozen=True` | 監査ログは履歴データであり変更されるべきでない。ハッシュ可能になりset/dictのキーに使用可能 |
| `extra="allow"` | GitHubは頻繁に新フィールドを追加するため、未知フィールドを破棄せず保持 |
| `AliasChoices` | APIの`@timestamp`とPython属性名`timestamp`の両方に対応 |
| `StrEnum` | 文字列比較が容易、JSON直接互換 |

---

## 3. データローダー設計

### 3.1 ローディング戦略

```
┌──────────────────────────────────────────────────────────────┐
│                    Loading Strategies                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Small Data (< 100MB)     Medium Data (100MB - 1GB)         │
│  ┌─────────────────┐      ┌─────────────────────────┐       │
│  │   Eager Load    │      │   Lazy Evaluation       │       │
│  │   (Polars/     │      │   (DuckDB / Polars     │       │
│  │    Pandas)      │      │    LazyFrame)           │       │
│  └─────────────────┘      └─────────────────────────┘       │
│                                                              │
│  Large Data (> 1GB)                                          │
│  ┌─────────────────────────────────────────────────┐        │
│  │              Streaming Batch                     │        │
│  │   (orjson + Generator + Chunk Processing)       │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 高速ローダー実装

```python
# src/audit_analyzer/loader.py（推奨実装）

from __future__ import annotations
import mmap
from pathlib import Path
from typing import Iterator, Any
from collections.abc import Generator

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False


def stream_audit_log_fast(
    path: Path,
    *,
    batch_size: int = 50_000,
) -> Generator[list[dict[str, Any]], None, None]:
    """メモリマップを使用した高速ストリーミング読み込み
    
    3-4GBのファイルでも約30秒で処理可能（orjson + mmap使用時）
    
    Args:
        path: NDJSONファイルパス
        batch_size: 1バッチあたりのエントリ数
        
    Yields:
        監査ログエントリの辞書リスト
    """
    with path.open("rb") as f:
        # メモリマップでファイル全体をマッピング（実際のメモリ使用は最小限）
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            batch: list[dict[str, Any]] = []
            
            for line in iter(mm.readline, b""):
                if not line.strip():
                    continue
                    
                entry = orjson.loads(line)
                batch.append(entry)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            if batch:
                yield batch


def load_with_duckdb_optimized(
    path: Path,
    *,
    columns: list[str] | None = None,
    where: str | None = None,
) -> Any:
    """DuckDBによる最適化された遅延読み込み
    
    列プッシュダウンとフィルタプッシュダウンにより
    必要なデータのみをメモリに読み込む
    
    Args:
        path: JSON/NDJSONファイルまたはディレクトリ
        columns: 読み込む列（Noneで全列）
        where: SQLのWHERE句条件
        
    Returns:
        DuckDB relation（遅延評価）
    """
    import duckdb
    
    conn = duckdb.connect(":memory:")
    
    # 列選択
    select_clause = ", ".join(columns) if columns else "*"
    
    # ファイルパターン
    if path.is_dir():
        pattern = str(path / "*.json")
    else:
        pattern = str(path)
    
    query = f"SELECT {select_clause} FROM read_json_auto('{pattern}')"
    
    if where:
        query += f" WHERE {where}"
    
    return conn.execute(query)


def load_incremental(
    path: Path,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> "pl.LazyFrame":
    """時間範囲を指定した増分読み込み
    
    大量データから特定期間のみを効率的に抽出
    
    Args:
        path: ファイルまたはディレクトリパス
        since: 開始日時（inclusive）
        until: 終了日時（exclusive）
        
    Returns:
        Polars LazyFrame
    """
    import polars as pl
    
    lf = pl.scan_ndjson(path)
    
    # タイムスタンプフィルタ（プッシュダウンされる）
    if since:
        lf = lf.filter(pl.col("@timestamp") >= since)
    if until:
        lf = lf.filter(pl.col("@timestamp") < until)
    
    return lf
```

### 3.3 パフォーマンス比較

| 方式 | 1GB処理時間 | メモリ使用量 | 用途 |
|-----|-----------|------------|------|
| `json.load()` | 60秒 | 8GB+ | 非推奨 |
| `orjson` + streaming | 15秒 | 500MB | 全件処理 |
| DuckDB lazy | 5秒 | 200MB | 集計・分析 |
| Polars LazyFrame | 8秒 | 300MB | DataFrame操作 |

---

## 4. 分析ロジック設計

### 4.1 アーキテクチャ

```
┌────────────────────────────────────────────────────────────────┐
│                      Analysis Pipeline                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────┐    ┌───────────────┐    ┌──────────────────┐    │
│  │  Loader  │───▶│  BaseAnalyzer │───▶│  Visualization   │    │
│  └──────────┘    └───────────────┘    │  (Altair/marimo) │    │
│                         │              └──────────────────┘    │
│                         ▼                                      │
│         ┌───────────────────────────────────┐                 │
│         │         Specialized Analyzers      │                 │
│         ├───────────────────────────────────┤                 │
│         │  • UserActivityAnalyzer           │                 │
│         │  • TimeSeriesAnalyzer             │                 │
│         │  • ActionTracker                  │                 │
│         │  • AnomalyDetector                │                 │
│         └───────────────────────────────────┘                 │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 ユーザー活動分析

```python
# src/audit_analyzer/analyzers/user_activity.py

class UserActivityAnalyzer(BaseAnalyzer):
    """ユーザー活動パターンの分析"""
    
    def get_top_users(
        self,
        n: int = 10,
        *,
        action_filter: str | None = None,
    ) -> dict[str, Any]:
        """最もアクティブなユーザーを取得
        
        DuckDB SQLで効率的に集計
        """
        if self._backend == "duckdb":
            query = f"""
                SELECT 
                    actor,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT action) as unique_actions,
                    MIN("@timestamp") as first_event,
                    MAX("@timestamp") as last_event,
                    COUNT(DISTINCT DATE_TRUNC('day', "@timestamp")) as active_days
                FROM audit_log
                {"WHERE action = '" + action_filter + "'" if action_filter else ""}
                GROUP BY actor
                ORDER BY event_count DESC
                LIMIT {n}
            """
            return self._conn.execute(query).fetchdf()
        
        # Polars実装
        return (
            self._df
            .group_by("actor")
            .agg([
                pl.len().alias("event_count"),
                pl.col("action").n_unique().alias("unique_actions"),
                pl.col("@timestamp").min().alias("first_event"),
                pl.col("@timestamp").max().alias("last_event"),
            ])
            .sort("event_count", descending=True)
            .head(n)
        )
    
    def get_user_timeline(
        self,
        user: str,
        *,
        granularity: str = "1h",
    ) -> "pl.DataFrame":
        """特定ユーザーの活動タイムライン
        
        Args:
            user: ユーザー名
            granularity: 集計粒度（"1h", "1d", "1w"）
        """
        return (
            self._df
            .filter(pl.col("actor") == user)
            .group_by_dynamic("@timestamp", every=granularity)
            .agg([
                pl.len().alias("event_count"),
                pl.col("action").mode().first().alias("most_common_action"),
            ])
        )
```

### 4.3 時間帯別分析

```python
# src/audit_analyzer/analyzers/time_series.py

class TimeSeriesAnalyzer(BaseAnalyzer):
    """時系列パターンの分析"""
    
    def get_hourly_distribution(self) -> dict[int, int]:
        """時間帯別イベント分布
        
        22:00-06:00, 週末のアクティビティを特定
        """
        if self._backend == "duckdb":
            query = """
                SELECT 
                    EXTRACT(HOUR FROM "@timestamp") as hour,
                    COUNT(*) as count,
                    CASE 
                        WHEN EXTRACT(HOUR FROM "@timestamp") < 6 
                          OR EXTRACT(HOUR FROM "@timestamp") >= 22 
                        THEN 'off_hours'
                        ELSE 'business_hours'
                    END as period_type
                FROM audit_log
                GROUP BY 1, 3
                ORDER BY 1
            """
            return self._conn.execute(query).fetchdf()
        
        return (
            self._df
            .with_columns([
                pl.col("@timestamp").dt.hour().alias("hour"),
                pl.when(
                    (pl.col("@timestamp").dt.hour() < 6) |
                    (pl.col("@timestamp").dt.hour() >= 22)
                )
                .then(pl.lit("off_hours"))
                .otherwise(pl.lit("business_hours"))
                .alias("period_type")
            ])
            .group_by(["hour", "period_type"])
            .agg(pl.len().alias("count"))
            .sort("hour")
        )
    
    def detect_activity_spikes(
        self,
        *,
        window: str = "1h",
        threshold_std: float = 3.0,
    ) -> list[dict[str, Any]]:
        """異常な活動スパイクを検出
        
        移動平均からの偏差が閾値を超えるイベントを特定
        """
        df = (
            self._df
            .group_by_dynamic("@timestamp", every=window)
            .agg(pl.len().alias("count"))
            .with_columns([
                pl.col("count").rolling_mean(window_size=24).alias("rolling_mean"),
                pl.col("count").rolling_std(window_size=24).alias("rolling_std"),
            ])
            .with_columns([
                ((pl.col("count") - pl.col("rolling_mean")) / pl.col("rolling_std"))
                .alias("z_score")
            ])
            .filter(pl.col("z_score").abs() > threshold_std)
        )
        
        return df.to_dicts()
```

### 4.4 アクション追跡

```python
# src/audit_analyzer/analyzers/action_tracker.py

class ActionTracker(BaseAnalyzer):
    """特定アクションの追跡と分析"""
    
    def track_dangerous_actions(self) -> "pl.DataFrame":
        """危険なアクションを追跡
        
        DANGEROUS_ACTIONS/HIGH_RISK_ACTIONSに該当するイベントを抽出
        """
        from audit_analyzer.utils.constants import (
            DANGEROUS_ACTIONS,
            HIGH_RISK_ACTIONS,
        )
        
        return (
            self._df
            .filter(
                pl.col("action").is_in(list(DANGEROUS_ACTIONS)) |
                pl.col("action").is_in(list(HIGH_RISK_ACTIONS))
            )
            .with_columns([
                pl.when(pl.col("action").is_in(list(DANGEROUS_ACTIONS)))
                .then(pl.lit("CRITICAL"))
                .otherwise(pl.lit("HIGH"))
                .alias("risk_level")
            ])
            .sort("@timestamp", descending=True)
        )
    
    def get_action_sequences(
        self,
        user: str,
        *,
        window_minutes: int = 30,
    ) -> list[list[str]]:
        """ユーザーのアクションシーケンスを抽出
        
        連続した操作パターンを特定（例：設定変更→メンバー追加→権限変更）
        """
        user_events = (
            self._df
            .filter(pl.col("actor") == user)
            .sort("@timestamp")
            .with_columns([
                (pl.col("@timestamp") - pl.col("@timestamp").shift(1))
                .dt.total_minutes()
                .alias("gap_minutes")
            ])
            .with_columns([
                (pl.col("gap_minutes") > window_minutes).cum_sum().alias("session_id")
            ])
        )
        
        # セッションごとにアクションをグループ化
        sessions = (
            user_events
            .group_by("session_id")
            .agg(pl.col("action").alias("actions"))
        )
        
        return sessions.get_column("actions").to_list()
```

### 4.5 異常検知

```python
# src/audit_analyzer/analyzers/anomaly.py（主要検出ロジック）

class AnomalyDetector(BaseAnalyzer):
    """包括的な異常検知"""
    
    def detect_all(self) -> AnomalyReport:
        """すべての異常検知を実行"""
        return AnomalyReport(
            dangerous_actions=self.detect_dangerous_actions(),
            off_hours_activity=self.detect_off_hours_activity(),
            bulk_operations=self.detect_bulk_operations(),
            unusual_ips=self.detect_unusual_ips(),
            rapid_operations=self.detect_rapid_operations(),
        )
    
    def detect_rapid_operations(
        self,
        *,
        window_minutes: int = 5,
    ) -> list[Anomaly]:
        """短時間での大量操作を検出
        
        5分間で50件以上の同一アクションを異常とみなす
        """
        from audit_analyzer.utils.constants import RAPID_OPERATION_THRESHOLDS
        
        anomalies = []
        
        # DuckDB SQLでウィンドウ集計
        query = f"""
            WITH windowed AS (
                SELECT 
                    actor,
                    action,
                    "@timestamp",
                    COUNT(*) OVER (
                        PARTITION BY actor, action
                        ORDER BY "@timestamp"
                        RANGE BETWEEN INTERVAL {window_minutes} MINUTE PRECEDING
                          AND CURRENT ROW
                    ) as window_count
                FROM audit_log
            )
            SELECT DISTINCT
                actor,
                action,
                MAX(window_count) as max_count
            FROM windowed
            GROUP BY actor, action
            HAVING MAX(window_count) > 50
        """
        
        results = self._conn.execute(query).fetchall()
        
        for actor, action, count in results:
            threshold = RAPID_OPERATION_THRESHOLDS.get(action, 50)
            if count > threshold:
                anomalies.append(Anomaly(
                    anomaly_type="rapid_operation",
                    risk_level=RiskLevel.HIGH,
                    description=f"{actor}が{window_minutes}分間で{action}を{count}回実行",
                    actor=actor,
                    details={"action": action, "count": count, "threshold": threshold},
                ))
        
        return anomalies
    
    def detect_first_time_actions(
        self,
        *,
        lookback_days: int = 90,
    ) -> list[Anomaly]:
        """ユーザーの初めてのアクションを検出
        
        過去90日間で実行したことのないアクションを検出
        """
        # 過去のアクション履歴を取得
        historical = (
            self._df
            .filter(
                pl.col("@timestamp") < (pl.col("@timestamp").max() - pl.duration(days=lookback_days))
            )
            .group_by("actor")
            .agg(pl.col("action").unique().alias("known_actions"))
        )
        
        # 直近のアクションと比較
        recent = (
            self._df
            .filter(
                pl.col("@timestamp") >= (pl.col("@timestamp").max() - pl.duration(days=1))
            )
        )
        
        # 初めてのアクションを特定
        first_time = (
            recent
            .join(historical, on="actor", how="left")
            .filter(~pl.col("action").is_in(pl.col("known_actions")))
        )
        
        return [
            Anomaly(
                anomaly_type="first_time_action",
                risk_level=RiskLevel.MEDIUM,
                description=f"{row['actor']}が初めて{row['action']}を実行",
                timestamp=row["@timestamp"],
                actor=row["actor"],
            )
            for row in first_time.to_dicts()
        ]
```

---

## 5. テストデータ生成

### 5.1 生成戦略

```
┌────────────────────────────────────────────────────────────────┐
│                   Test Data Generation                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Weighted Action Distribution:                                 │
│  ├── Git操作 (40%): clone, push, fetch                        │
│  ├── リポジトリ操作 (15%): create, access, settings           │
│  ├── 組織管理 (10%): member ops, team ops                     │
│  ├── セキュリティ (5%): secret scanning, code scanning        │
│  └── その他 (30%): workflows, pull_request, etc.              │
│                                                                │
│  Anomaly Injection:                                            │
│  ├── 時間外活動 (22:00-06:00, 週末): 2-5%                     │
│  ├── バルク操作 (5分で50+件): 0.5-1%                          │
│  ├── 不審IP (外部/VPN): 1-2%                                   │
│  └── 危険アクション: 0.1-0.5%                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 使用方法

```bash
# 基本的な生成（10,000件）
python scripts/generate_test_data.py --count 10000 --output data/test_audit.json

# 異常を含むデータ生成
python scripts/generate_test_data.py \
    --count 50000 \
    --days 30 \
    --inject-anomalies \
    --anomaly-rate 0.05 \
    --output data/test_with_anomalies.ndjson

# 再現可能なデータ生成
python scripts/generate_test_data.py \
    --count 100000 \
    --seed 42 \
    --output data/reproducible_test.ndjson
```

---

## 6. marimo ノートブック統合

### 6.1 インタラクティブダッシュボード

```python
# notebooks/dashboard.py

import marimo as mo
import altair as alt
from audit_analyzer.loader import load_audit_log_lazy
from audit_analyzer.analyzers import AnomalyDetector, UserActivityAnalyzer

# データ読み込み（UIウィジェットでパス選択）
file_path = mo.ui.text(value="data/audit_log.ndjson", label="Audit Log Path")

@mo.cell
def load_data():
    df = load_audit_log_lazy(file_path.value).collect()
    return df

# 異常検知ダッシュボード
@mo.cell
def anomaly_dashboard(df):
    detector = AnomalyDetector(df)
    report = detector.detect_all()
    
    # リスクサマリーチャート
    risk_chart = alt.Chart(report.to_summary_df()).mark_bar().encode(
        x="risk_level:N",
        y="count:Q",
        color="risk_level:N"
    )
    
    return mo.vstack([
        mo.md(f"## 検出された異常: {report.total_count}件"),
        risk_chart,
        mo.ui.table(report.anomalies[:100])
    ])
```

---

## 7. パフォーマンス最適化ガイド

### 7.1 メモリ管理

| データサイズ | 推奨アプローチ |
|------------|--------------|
| < 100MB | Polars eager load |
| 100MB - 1GB | DuckDB / Polars lazy |
| > 1GB | Streaming + batch processing |

### 7.2 クエリ最適化

```python
# ❌ 非効率（全データをメモリに読み込む）
df = pl.read_ndjson("data/audit.ndjson")
result = df.filter(pl.col("action") == "repo.destroy")

# ✅ 効率的（フィルタがプッシュダウンされる）
lf = pl.scan_ndjson("data/audit.ndjson")
result = lf.filter(pl.col("action") == "repo.destroy").collect()

# ✅ DuckDBでさらに効率的
conn.execute("""
    SELECT * FROM read_json_auto('data/audit.ndjson')
    WHERE action = 'repo.destroy'
""")
```

---

## 8. 今後の拡張

1. **リアルタイム分析**: GitHub Webhookとの統合
2. **機械学習異常検知**: Isolation Forest / LSTM
3. **アラート統合**: Slack / PagerDuty
4. **コンプライアンスレポート**: SOC2 / GDPR準拠レポート自動生成
