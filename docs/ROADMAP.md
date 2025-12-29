# ロードマップ

将来的に実装を検討している機能と改善点をまとめています。

---

## 🎯 優先度: 高

### 複数JSONファイルのロード対応

**概要**: 複数の監査ログファイルを選択して一括でロードできるようにする

**現状**:
- 現在は1ファイルのみ選択可能（`mo.ui.file()`）

**実装案**:
```python
# 複数ファイル選択を有効化
file_input = mo.ui.file(
    filetypes=[".json", ".ndjson"],
    multiple=True,  # 複数選択を有効化
    label="監査ログファイルを選択（複数可）",
)

# 複数ファイルの結合
if file_input.value:
    all_data = []
    for file in file_input.value:
        content = file.contents.decode("utf-8").strip()
        if content.startswith("["):
            all_data.extend(json.loads(content))
        else:
            all_data.extend([
                json.loads(line)
                for line in content.split("\n")
                if line.strip()
            ])
    df = pl.DataFrame(all_data)
```

**対象ノートブック**:
- `notebooks/index.py`
- その他必要に応じて

**工数見積もり**: 1-2時間

---

## 🔬 優先度: 中

### marimoノートブックの自動テスト

**概要**: notebooks/の品質を自動テストで担保する

**テスト戦略（レベル別）**:

| レベル | 内容 | 工数 |
|--------|------|------|
| Level 0 | 構文チェック（`py_compile`） | 実装済み（CI） |
| Level 1 | インポートテスト | 1時間 |
| Level 2 | アプリ生成テスト | 2時間 |
| Level 3 | セル実行テスト | 4時間 |
| Level 4 | E2Eテスト（Playwright） | 8時間以上 |

**実装ファイル**:
```
tests/
├── test_notebooks_syntax.py      # Level 0-1
├── test_notebooks_execution.py   # Level 2-3
└── conftest.py                   # フィクスチャ
```

**詳細な計画**: [docs/copilot/PLAN.md](copilot/PLAN.md) を参照

---

## 💡 優先度: 低

### データフィルタリング機能の強化

- 日付範囲でのフィルタリング
- 複数条件の組み合わせ（AND/OR）
- フィルタプリセットの保存

### エクスポート機能

- フィルタ済みデータのCSV/JSONエクスポート
- チャートの画像エクスポート
- レポートPDF生成

### パフォーマンス改善

- 大規模データ（100万件以上）での動作最適化
- 遅延読み込み（Polars LazyFrame活用）
- キャッシュ機構の導入

---

## 📝 アイデアメモ

実装するか未定だが、検討中のアイデア：

- [ ] ダークモード対応
- [ ] 多言語対応（英語/日本語）
- [ ] カスタムダッシュボード作成機能
- [ ] アラート通知（危険アクション検出時）
- [ ] データ比較機能（期間間の差分分析）

---

## 更新履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-29 | 初版作成 |
