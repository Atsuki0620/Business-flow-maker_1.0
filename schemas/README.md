# schemas ディレクトリ

業務フロー生成で使用するJSON Schemaの定義ファイルを格納しています。

## ファイル一覧

### flow.schema.json

業務フローの独自JSON形式の定義（JSON Schema Draft 2020-12準拠）。LLMによるJSON生成時の型安全性と整合性を保証します。

## スキーマ仕様（flow.schema.json）

### トップレベルフィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `metadata` | object | × | メタデータ（ID、タイトル、更新日時、生成情報） |
| `actors` | array | ○ | 業務実施者・システム（最低1件必要） |
| `phases` | array | ○ | 業務フェーズ・工程（最低1件必要） |
| `tasks` | array | ○ | 具体的な作業・タスク（最低1件必要） |
| `gateways` | array | × | 分岐・合流の制御要素（BPMN 2.0準拠） |
| `flows` | array | ○ | タスク間の遷移（最低1件必要） |
| `issues` | array | × | 曖昧点や不明点の記録 |

### 主要フィールドの詳細

#### actors（業務実施者）

```json
{
  "id": "actor_sales_staff",
  "name": "営業担当者",
  "type": "human",
  "notes": "全国の営業拠点に配置"
}
```

- **id**: 一意識別子（snake_case推奨）
- **name**: 表示名
- **type**: `human`（人間）、`system`（システム）、`bot`（ボット）、`group`（グループ）
- **notes**: 補足説明（任意）

#### phases（業務フェーズ）

```json
{
  "id": "phase_approval",
  "name": "承認フェーズ",
  "description": "上長による承認プロセス"
}
```

- **id**: 一意識別子
- **name**: 表示名
- **description**: フェーズの詳細説明（任意）

#### tasks（タスク）

```json
{
  "id": "task_submit_application",
  "name": "申請書提出",
  "actor_id": "actor_sales_staff",
  "phase_id": "phase_application",
  "raci": "R",
  "handoff_to": ["actor_manager"],
  "systems": ["申請システム"],
  "notes": "期限は月末まで"
}
```

- **id**: 一意識別子
- **name**: タスク名
- **actor_id**: 実施者のID（`actors[].id`を参照）
- **phase_id**: 所属フェーズのID（`phases[].id`を参照）
- **raci**: RACI分類（`R`：実行、`A`：承認、`C`：相談、`I`：情報共有）（任意）
- **handoff_to**: 引継ぎ先のactor IDリスト（任意）
- **systems**: 使用するシステムのリスト（任意）
- **notes**: 補足説明（任意）

#### gateways（ゲートウェイ）

```json
{
  "id": "gateway_amount_check",
  "name": "金額判定",
  "type": "exclusive",
  "notes": "10万円以上の場合は上長承認へ"
}
```

- **id**: 一意識別子
- **name**: ゲートウェイ名
- **type**: `exclusive`（排他的分岐）、`parallel`（並行分岐）、`inclusive`（包含的分岐）
- **notes**: 判定条件の詳細（任意）

#### flows（フロー）

```json
{
  "id": "flow_001",
  "from": "task_submit_application",
  "to": "gateway_amount_check",
  "condition": "申請後",
  "notes": "自動的に判定処理へ"
}
```

- **id**: 一意識別子
- **from**: 開始ノードのID（`tasks[].id`または`gateways[].id`）
- **to**: 終了ノードのID（`tasks[].id`または`gateways[].id`）
- **condition**: 遷移条件（任意）
- **notes**: 補足説明（任意）

#### issues（課題・不明点）

```json
{
  "id": "issue_001",
  "note": "承認期限が不明",
  "severity": "warning"
}
```

- **id**: 一意識別子
- **note**: 課題や不明点の内容
- **severity**: `info`（情報）、`warning`（警告）、`critical`（重大）

## 命名規則とベストプラクティス

### 命名規則
- **キー名**: `snake_case`（例: `actor_id`, `phase_id`）
- **ID値**: `{prefix}_{descriptive_name}`（例: `task_submit_application`, `actor_sales_staff`）

### ベストプラクティス
1. **欠落情報の扱い**: 不明な情報は`issues[].note`に明示する
2. **参照整合性**: すべての`actor_id`と`phase_id`は存在する`actors[].id`と`phases[].id`を参照する
3. **タスクとゲートウェイの使い分け**:
   - 実作業 → `tasks`
   - 判定・分岐 → `gateways`
4. **空配列の扱い**: `handoff_to`と`systems`は空配列でも必ず含める

## バージョン管理

現在のスキーマバージョン: **v1.0** (2025-11-13)

### 変更履歴
- **v1.0** (2025-11-13): 初版リリース
  - 基本フィールド定義（actors, phases, tasks, flows, issues）
  - gatewaysフィールドの追加（BPMN 2.0対応）
  - metadataフィールドの追加（生成情報記録）

### 今後の拡張予定
- バージョン番号フィールドの追加
- 外部参照スキーマのサポート
- カスタムバリデーションルールの定義
