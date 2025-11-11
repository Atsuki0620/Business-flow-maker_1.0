# 可視化レイヤー改善計画

**Last Updated:** 2025-11-12
**Version:** v0.38

## 概要

本ドキュメントは、HTML/Mermaid可視化における技術的問題と改善計画を記録する。

## 背景

`runs/20251111_235939_sample-tiny-01` の実行結果検証において、以下の問題が確認された：

1. **SVG可視化**: ノードとゲートウェイが重なって表示される
2. **Mermaid可視化**: ゲートウェイ（`gateway_amount`）が2か所定義され、1つが独立して前後関係がない
3. **データモデル**: タスクとゲートウェイの責務が混在している

これらは将来的にBPMN準拠の確定形を実装する際に根本解決すべき問題だが、現時点で対処可能な部分については早期修正を行う。

---

## 問題分析

### 1. HTML Visualizer: ノード重なり問題

**ファイル:** `src/visualizers/html_visualizer.py:84-98`

**問題:**
同一phase内の複数タスクが同一座標 (x, y) に配置され、視覚的に重なる。

**原因:**
```python
# Line 88-89
x = MARGIN_X + LANE_HEADER_WIDTH + phase_idx * (TASK_WIDTH + COLUMN_GAP)
y = lane_top + (LANE_HEIGHT - TASK_HEIGHT) / 2
```
- すべてのタスクがphase_idxのみでX座標を決定
- phase内に複数タスクがある場合、Y座標が完全に同一

**実例:**
`runs/20251111_235939_sample-tiny-01/output/flow.svg` で申請準備フェーズの3タスクが完全に重なっている。

**影響度:** 高（ユーザー体験を著しく損なう）

---

### 2. Mermaid Visualizer: ゲートウェイ孤立問題

**ファイル:** `src/visualizers/mermaid_visualizer.py:52-57`

**問題:**
`gateways` 配列の要素が独立したダイヤモンド型ノードとして定義されるが、`flows` 配列との関連付けが欠如。

**該当コード:**
```python
# Lines 52-57
gateways = flow_data.get("gateways", [])
for gateway in gateways:
    gw_id = gateway["id"]
    gw_name = sanitize_label(gateway["name"])
    lines.append(f'    {gw_id}{{"{gw_name}"}}')
```

**実例:**
`runs/20251111_235939_sample-tiny-01/output/flow.mmd:11` に `gateway_amount{"金額判定"}` が定義されているが、実際のフロー（lines 13-19）では `task_amount_judgment` から直接分岐しており、ゲートウェイノードが孤立。

**根本原因:**
LLMがタスクとゲートウェイの違いを理解していない、またはプロンプトで明確に指示されていない。

**影響度:** 中（混乱を招くが、フロー自体は理解可能）

---

### 3. Few-shot Example: モデル不整合

**ファイル:** `samples/expected/sample-tiny-01.json:51-134`

**問題:**
- `task_amount_judgment`（金額判定タスク）と `gateway_amount`（金額判定ゲートウェイ）が併存
- `flows` では `task_amount_judgment` から直接分岐しており、ゲートウェイが使用されていない

**問題点:**
Few-shot example 自体がゲートウェイの誤った使い方を示しており、LLMがこのパターンを学習してしまう。

**影響度:** 高（LLM生成品質の根本原因）

---

### 4. LLMプロンプト: ゲートウェイの定義不足

**ファイル:** `src/core/generator.py:73-83`

**現状のシステムプロンプト:**
```python
"あなたは業務フローアーキテクトです。\n"
"業務文書を読み、actors / phases / tasks / flows / gateways / issues / metadata を含む JSON を生成してください。\n\n"
"必須ルール:\n"
"1. JSON Schema に準拠し、snake_case キーを維持する\n"
"2. tasks と flows の ID は対応させる（flows[].from/to は必ず tasks[].id または gateways[].id を参照）\n"
"..."
```

**問題:**
- 「ゲートウェイとは何か」「いつ使うべきか」が説明されていない
- 「判定処理はタスクではなくゲートウェイとして表現する」という指示がない
- BPMNの概念説明がない

**影響度:** 高（LLM生成品質の根本原因）

---

## Phase 1: クイックフィックス（v0.38）

### 1.1 HTML: ノード重なり修正

**状態:** ✅ 完了

**修正内容:**
同一phase内のタスクをY方向にオフセットして配置。

**実装:**
```python
# phase内のタスク順序を追跡
phase_task_counters = {}
for task in flow.get("tasks", []):
    phase_id = task.get("phase_id")
    task_order = phase_task_counters.get(phase_id, 0)
    y_offset = task_order * (TASK_HEIGHT + 10)  # 10px間隔
    phase_task_counters[phase_id] = task_order + 1
```

**見積工数:** 30分
**実工数:** （完了後に記録）

---

### 1.2 Mermaid: ゲートウェイ孤立修正

**状態:** ✅ 完了

**修正内容:**
フローに接続されていないゲートウェイ定義をスキップ（暫定対策）。

**理由:**
現状のJSONではゲートウェイが正しく使われていないため、孤立ノードを非表示にすることで混乱を回避。根本対策はPhase 2で実施。

**見積工数:** 15分
**実工数:** （完了後に記録）

---

### 1.3 Few-shot Example 修正

**状態:** ✅ 完了

**修正内容:**
- `task_amount_judgment` を削除
- `gateway_amount` をフローに統合
- `flows` を修正: `task_create_request` → `gateway_amount` → 分岐先

**変更前:**
```json
{
  "tasks": [
    {"id": "task_amount_judgment", "name": "金額判定", ...},
    ...
  ],
  "flows": [
    {"from": "task_create_request", "to": "task_amount_judgment"},
    {"from": "task_amount_judgment", "to": "task_manager_approval", "condition": "10万円以上"},
    ...
  ]
}
```

**変更後:**
```json
{
  "gateways": [
    {"id": "gateway_amount", "name": "金額判定", "type": "exclusive"}
  ],
  "flows": [
    {"from": "task_create_request", "to": "gateway_amount"},
    {"from": "gateway_amount", "to": "task_manager_approval", "condition": "10万円以上"},
    ...
  ]
}
```

**見積工数:** 20分
**実工数:** （完了後に記録）

---

### 1.4 LLMプロンプト改善

**状態:** ✅ 完了

**修正内容:**
システムプロンプトにゲートウェイの定義と使用ルールを追加。

**追加ルール:**
```python
"7. ゲートウェイ (gateways) の使用ルール:\n"
"   - 判定・分岐処理はタスクではなくゲートウェイとして表現する\n"
"   - ゲートウェイとタスクを重複させない（例: 「金額判定」はゲートウェイのみ）\n"
"   - ゲートウェイの type は exclusive（排他的）/ parallel（並行）/ inclusive（包含的）から選択\n"
"   - ゲートウェイには必ず2つ以上の出力フローが必要\n"
```

**見積工数:** 1時間
**実工数:** （完了後に記録）

---

## Phase 2: 根本対策（v0.4x）

以下は次期バージョンで対応予定。

### 2.1 HTML: ゲートウェイ配置アルゴリズム改善

**概要:**
- フロー解析による位相ソート（topological sort）を実装
- ゲートウェイを接続元タスクと接続先タスクの中間位置に配置
- `infer_phase_idx()` / `infer_actor_idx()` の再帰を廃止

**見積工数:** 2-3時間

---

### 2.2 正規化処理の追加

**概要:**
- `normalize_flow_document()` で判定タスクをゲートウェイに自動変換
- `flows` の整合性チェック（ゲートウェイへの入出力フロー数の検証）

**見積工数:** 2時間

---

### 2.3 HTML: レイアウトエンジン改善

**概要:**
- Sugiyama-style layering 実装
- 列（column）の自動調整
- エッジルーティングの改善（オルソゴナルルーティング）
- elk.js 導入の検討

**見積工数:** 4-6時間

---

## 決定事項ログ

| 日付 | 決定内容 | 理由 |
|------|---------|------|
| 2025-11-12 | Phase 1でLLMプロンプト改善を含める | ユーザー要望により、根本対策を早期実施 |
| 2025-11-12 | Mermaid修正は暫定対策（孤立ゲートウェイ非表示） | 根本対策（フロー構造変更）はPhase 2で実施 |
| 2025-11-12 | 全サンプルで検証を実施 | 品質保証のため、複数パターンでの動作確認が必要 |
| 2025-11-12 | 新規ブランチ `feat/fix-visualization-v038` 作成 | 独立した機能改善として管理 |

---

## 検証結果

### 検証環境

- Python: 3.x
- Model: gpt-4o-mini
- Samples: sample-tiny-01, sample-medium-01

### 検証項目

- [ ] sample-tiny-01: ノード重なり解消確認
- [ ] sample-tiny-01: Mermaidゲートウェイ孤立解消確認
- [ ] sample-medium-01: 複雑なフローでの動作確認
- [ ] その他サンプル: 異常がないか確認

### 検証結果

（検証完了後に記録）

---

## 参考資料

- BPMN 2.0 Specification: https://www.omg.org/spec/BPMN/2.0/
- Sugiyama-style Layering: https://en.wikipedia.org/wiki/Layered_graph_drawing
- elk.js: https://github.com/kieler/elkjs

---

**Document End**
