# DuckDB/Polars クエリの最適化

このプロンプトを使用して、DuckDBまたはPolarsクエリを最適化してください。

## 入力情報

最適化対象について以下を指定してください：

- **現在のクエリ**: {{current_query}}
- **データサイズ**: {{data_size}} (例: 100万件, 3GB)
- **パフォーマンス問題**: {{performance_issue}}
- **使用バックエンド**: {{backend}} (DuckDB / Polars / 両方)

## DuckDB最適化パターン

### 1. ファイル直接読み込み

```sql
-- ❌ Bad: Pythonでの前処理後にDuckDBへ
-- Python側でJSONを読み込んでからDuckDBに渡す

-- ✅ Good: DuckDBで直接読み込み
SELECT * FROM read_json_auto('data/audit_log.json');

-- ✅ Good: NDJSON形式（大規模データ向け）
SELECT * FROM read_ndjson_auto('data/audit_log.ndjson');

-- ✅ Good: 複数ファイルのglobパターン
SELECT * FROM read_json_auto('data/audit_log_*.json');
```

### 2. 列選択の最適化

```sql
-- ❌ Bad: 全列選択
SELECT * FROM audit_logs WHERE action = 'repo.create';

-- ✅ Good: 必要な列のみ選択
SELECT timestamp, actor, action, repo
FROM audit_logs
WHERE action = 'repo.create';
```

### 3. フィルタの早期適用

```sql
-- ❌ Bad: 集計後にフィルタ
SELECT actor, COUNT(*) as cnt
FROM audit_logs
GROUP BY actor
HAVING COUNT(*) > 100;

-- ✅ Good: 事前フィルタでデータ量を削減
SELECT actor, COUNT(*) as cnt
FROM audit_logs
WHERE timestamp >= '2024-01-01'
  AND action NOT IN ('git.clone', 'git.fetch')  -- 高頻度アクションを除外
GROUP BY actor
HAVING cnt > 100;
```

### 4. インデックス/パーティショニング

```sql
-- 大規模データ向け: Parquet形式 + パーティショニング
COPY (
    SELECT *,
           EXTRACT(YEAR FROM timestamp) as year,
           EXTRACT(MONTH FROM timestamp) as month
    FROM read_json_auto('data/audit_log.json')
)
TO 'data/partitioned'
(FORMAT PARQUET, PARTITION_BY (year, month));

-- パーティションを活用したクエリ
SELECT * FROM read_parquet('data/partitioned/year=2024/month=12/*.parquet');
```

### 5. 集計の最適化

```sql
-- ❌ Bad: サブクエリの多用
SELECT
    actor,
    (SELECT COUNT(*) FROM audit_logs a2 WHERE a2.actor = a1.actor) as total_actions
FROM audit_logs a1
GROUP BY actor;

-- ✅ Good: ウィンドウ関数
SELECT DISTINCT
    actor,
    COUNT(*) OVER (PARTITION BY actor) as total_actions
FROM audit_logs;

-- ✅ Better: 単純なGROUP BY
SELECT actor, COUNT(*) as total_actions
FROM audit_logs
GROUP BY actor;
```

## Polars最適化パターン

### 1. 遅延評価（LazyFrame）

```python
import polars as pl

# ❌ Bad: 即時評価
df = pl.read_json("data/audit_log.json")
df = df.filter(pl.col("action") == "repo.create")
df = df.select(["timestamp", "actor"])
result = df.group_by("actor").agg(pl.len())

# ✅ Good: 遅延評価（クエリプランの最適化）
result = (
    pl.scan_ndjson("data/audit_log.ndjson")
    .filter(pl.col("action") == "repo.create")
    .select(["timestamp", "actor"])
    .group_by("actor")
    .agg(pl.len())
    .collect()  # ここで初めて実行
)
```

### 2. 型の最適化

```python
# ❌ Bad: 文字列のまま処理
df = df.with_columns(
    pl.col("timestamp").str.to_datetime()
)

# ✅ Good: スキーマ指定で読み込み時に型変換
schema = {
    "timestamp": pl.Datetime,
    "actor": pl.Utf8,
    "action": pl.Categorical,  # 繰り返し値はCategoricalに
}
df = pl.read_json("data/audit_log.json", schema=schema)
```

### 3. 列選択の最適化

```python
# ❌ Bad: 全列読み込み後に選択
df = pl.read_json("file.json")
df = df.select(["col1", "col2"])

# ✅ Good: 読み込み時に列指定（LazyFrame）
df = (
    pl.scan_ndjson("file.ndjson")
    .select(["col1", "col2"])
    .collect()
)
```

### 4. 効率的な文字列操作

```python
# ❌ Bad: apply（Python関数呼び出し）
df = df.with_columns(
    pl.col("action").map_elements(lambda x: x.split(".")[0])
)

# ✅ Good: Polarsネイティブ関数
df = df.with_columns(
    pl.col("action").str.split(".").list.first().alias("category")
)
```

### 5. メモリ効率的な結合

```python
# ❌ Bad: 大きなDataFrame同士の結合
result = df1.join(df2, on="key")

# ✅ Good: 小さい方を右に
result = large_df.join(small_df, on="key")

# ✅ Better: セミ結合（存在チェックのみ）
result = large_df.join(
    small_df.select("key").unique(),
    on="key",
    how="semi"
)
```

### 6. 並列処理の活用

```python
# 複数ファイルの並列読み込み
from pathlib import Path

files = list(Path("data").glob("audit_log_*.ndjson"))

# ❌ Bad: 順次処理
dfs = [pl.read_ndjson(f) for f in files]
df = pl.concat(dfs)

# ✅ Good: 遅延評価で並列化
df = pl.concat([
    pl.scan_ndjson(f)
    for f in files
]).collect()
```

## パフォーマンス計測

### DuckDB

```python
import duckdb
import time

# EXPLAINでクエリプラン確認
print(duckdb.sql("EXPLAIN SELECT ...").fetchall())

# 実行時間計測
start = time.perf_counter()
result = duckdb.sql("SELECT ...").pl()
elapsed = time.perf_counter() - start
print(f"Elapsed: {elapsed:.3f}s, Rows: {len(result):,}")
```

### Polars

```python
import polars as pl

# クエリプラン確認（LazyFrame）
lazy_df = pl.scan_ndjson("file.ndjson").filter(...)
print(lazy_df.explain())  # 論理プラン
print(lazy_df.explain(optimized=True))  # 最適化後プラン

# プロファイリング
result = lazy_df.profile()
print(result[1])  # 実行統計
```

## 最適化チェックリスト

### 共通

- [ ] 必要な列のみ選択しているか
- [ ] フィルタは可能な限り早く適用しているか
- [ ] 適切なデータ型を使用しているか
- [ ] 不要な中間結果を作成していないか

### DuckDB

- [ ] `read_json_auto` でファイル直接読み込みしているか
- [ ] 大規模データはParquet形式に変換しているか
- [ ] サブクエリを最小限に抑えているか

### Polars

- [ ] `scan_*` + `collect()` の遅延評価を使用しているか
- [ ] `map_elements` (Python UDF) を避けているか
- [ ] Categorical型を適切に使用しているか
- [ ] 複数ファイルは並列読み込みしているか

## よくあるパフォーマンス問題と解決策

| 問題 | 原因 | 解決策 |
|------|------|--------|
| 読み込みが遅い | JSON形式 | NDJSON/Parquetに変換 |
| メモリ不足 | 全データ読み込み | LazyFrame/ストリーミング |
| 集計が遅い | 文字列比較 | Categorical型に変換 |
| 結合が遅い | 大きなDF同士 | セミ結合/フィルタ後結合 |
| UDF使用 | Python関数呼び出し | ネイティブ関数に置換 |
