# Business-flow-maker: データモデル概念定義

[最終更新日] 2025-11-12

## 目的

本ドキュメントでは、Business-flow-makerで使用するデータモデルの概念をBPMN 2.0仕様に基づいて明確に定義します。
特に**タスク**と**ゲートウェイ**の使い分けを明確化し、一貫性のあるフローJSON生成を実現します。

---

## 1. 基本概念の定義

### 1.1 タスク (Task)

**定義**: 人間またはシステムが実行する具体的な作業単位。

**特徴**:
- 実際の作業や操作を表す
- 時間とリソースを消費する活動
- 成果物や状態変化を生み出す
- 1つの入力フローと1つの出力フローを持つ（基本形）

**例**:
- ✅ 「申請書作成」（人間が申請書を作成する作業）
- ✅ 「見積取得」（業者から見積書を取得する作業）
- ✅ 「部長承認」（部長が内容を確認し承認する作業）
- ✅ 「発注処理」（システムまたは人間が発注を実行する作業）
- ✅ 「データ検証」（システムが入力データの妥当性を確認する作業）

**非該当例**:
- ❌ 「金額判定」（判定はゲートウェイ）
- ❌ 「条件分岐」（分岐制御はゲートウェイ）
- ❌ 「承認可否判定」（判定結果に基づく分岐はゲートウェイ）

---

### 1.2 ゲートウェイ (Gateway)

**定義**: フローの分岐・合流を制御する要素。判定ロジックそのものを表現する。

**特徴**:
- 作業を行わない（意思決定や条件評価のみ）
- フローの流れを制御する
- 複数の出力フローを持つ（分岐）または複数の入力フローを持つ（合流）
- BPMN 2.0では菱形（◇）で表現される

**ゲートウェイの種類**:

#### 1.2.1 排他的ゲートウェイ (Exclusive Gateway)
- **type**: `"exclusive"`
- **動作**: 複数の出力フローのうち、条件に合致する1つのみを実行
- **使用場面**: 「AまたはB」の選択、条件分岐
- **記法**: `⊗` (XOR)

**例**:
```json
{
  "id": "gateway_amount_check",
  "name": "10万円以上か判定",
  "type": "exclusive",
  "notes": "購入金額が10万円以上の場合は部長承認ルートへ"
}
```

対応フロー:
```json
[
  {"id": "flow_1", "from": "gateway_amount_check", "to": "task_manager_approval", "condition": "10万円以上"},
  {"id": "flow_2", "from": "gateway_amount_check", "to": "task_general_affairs", "condition": "10万円未満"}
]
```

#### 1.2.2 並行ゲートウェイ (Parallel Gateway)
- **type**: `"parallel"`
- **動作**: すべての出力フローを同時に実行（並行処理）
- **使用場面**: 複数タスクの同時実行、並行作業の開始・合流
- **記法**: `+` (AND)

**例**:
```json
{
  "id": "gateway_parallel_start",
  "name": "並行処理開始",
  "type": "parallel",
  "notes": "IT部門とHR部門が同時に準備作業を開始"
}
```

対応フロー:
```json
[
  {"id": "flow_1", "from": "gateway_parallel_start", "to": "task_it_setup"},
  {"id": "flow_2", "from": "gateway_parallel_start", "to": "task_hr_paperwork"}
]
```

#### 1.2.3 包含的ゲートウェイ (Inclusive Gateway)
- **type**: `"inclusive"`
- **動作**: 複数の出力フローのうち、条件に合致するすべてを実行
- **使用場面**: 「Aかつ/またはB」の選択、複数条件の評価
- **記法**: `○` (OR)

**例**:
```json
{
  "id": "gateway_notification",
  "name": "通知先判定",
  "type": "inclusive",
  "notes": "必要に応じて複数部署に通知"
}
```

対応フロー:
```json
[
  {"id": "flow_1", "from": "gateway_notification", "to": "task_notify_manager", "condition": "管理職への通知が必要"},
  {"id": "flow_2", "from": "gateway_notification", "to": "task_notify_accounting", "condition": "経理への通知が必要"},
  {"id": "flow_3", "from": "gateway_notification", "to": "task_notify_legal", "condition": "法務への通知が必要"}
]
```

---

### 1.3 フロー (Flow)

**定義**: タスクやゲートウェイ間の接続関係。シーケンスフローとも呼ばれる。

**特徴**:
- `from` (始点) と `to` (終点) で方向性を持つ
- オプションで `condition` (条件) を持つ（ゲートウェイからの分岐時）
- タスク → タスク、タスク → ゲートウェイ、ゲートウェイ → タスクなどの接続を表現

**例**:
```json
{
  "id": "flow_1",
  "from": "task_create_request",
  "to": "gateway_amount_check"
}
```

---

## 2. タスクとゲートウェイの使い分けガイドライン

### 2.1 判定基準フローチャート

```
業務要素を分析
    ↓
┌─────────────────┐
│実際の作業や操作か?│
└─────┬───────────┘
      │YES → タスク
      │
      │NO
      ↓
┌─────────────────┐
│判定・分岐処理か?  │
└─────┬───────────┘
      │YES → ゲートウェイ
      │
      │NO → 再検討
```

### 2.2 具体的な判断ルール

| 業務内容 | 分類 | 理由 |
|---------|------|------|
| 申請書を作成する | タスク | 実際の作業 |
| 見積を取得する | タスク | 実際の作業 |
| 金額が10万円以上か判定する | ゲートウェイ | 判定・分岐 |
| 部長が承認する | タスク | 承認作業そのもの |
| 承認結果に基づいて分岐する | ゲートウェイ | 判定・分岐 |
| システムが自動判定する | ゲートウェイ | 判定・分岐 |
| データを検証する | タスク | 検証作業（結果を記録） |
| 検証結果に基づいて分岐する | ゲートウェイ | 判定・分岐 |
| 複数部署に同時依頼する | ゲートウェイ (parallel) | 並行処理の開始 |
| 発注処理を実行する | タスク | 実際の作業 |

---

## 3. よくある誤用パターンと修正例

### 3.1 誤用パターン1: 判定処理をタスクとして定義

❌ **誤り**:
```json
{
  "tasks": [
    {"id": "task_amount_check", "name": "金額判定", ...},
    {"id": "task_manager_approval", "name": "部長承認", ...}
  ],
  "flows": [
    {"id": "flow_1", "from": "task_amount_check", "to": "task_manager_approval", "condition": "10万円以上"}
  ]
}
```

✅ **正しい**:
```json
{
  "tasks": [
    {"id": "task_manager_approval", "name": "部長承認", ...}
  ],
  "gateways": [
    {"id": "gateway_amount", "name": "10万円判定", "type": "exclusive"}
  ],
  "flows": [
    {"id": "flow_1", "from": "gateway_amount", "to": "task_manager_approval", "condition": "10万円以上"}
  ]
}
```

---

### 3.2 誤用パターン2: タスクとゲートウェイの重複定義

❌ **誤り**:
```json
{
  "tasks": [
    {"id": "task_approval_decision", "name": "承認可否判定", ...}
  ],
  "gateways": [
    {"id": "gateway_approval", "name": "承認可否判定", "type": "exclusive"}
  ]
}
```

✅ **正しい** (承認作業と判定を分離):
```json
{
  "tasks": [
    {"id": "task_manager_review", "name": "部長承認判断", "notes": "申請内容を確認し承認/却下を判断"}
  ],
  "gateways": [
    {"id": "gateway_approval_result", "name": "承認結果分岐", "type": "exclusive"}
  ],
  "flows": [
    {"id": "flow_1", "from": "task_manager_review", "to": "gateway_approval_result"},
    {"id": "flow_2", "from": "gateway_approval_result", "to": "task_next_step", "condition": "承認"},
    {"id": "flow_3", "from": "gateway_approval_result", "to": "task_reject_process", "condition": "却下"}
  ]
}
```

---

### 3.3 誤用パターン3: 並行処理を直列タスクで表現

❌ **誤り** (IT部門とHR部門が実際には並行作業なのに直列で定義):
```json
{
  "flows": [
    {"id": "flow_1", "from": "task_start", "to": "task_it_setup"},
    {"id": "flow_2", "from": "task_it_setup", "to": "task_hr_paperwork"}
  ]
}
```

✅ **正しい**:
```json
{
  "gateways": [
    {"id": "gateway_parallel_start", "type": "parallel"},
    {"id": "gateway_parallel_join", "type": "parallel"}
  ],
  "flows": [
    {"id": "flow_1", "from": "task_start", "to": "gateway_parallel_start"},
    {"id": "flow_2", "from": "gateway_parallel_start", "to": "task_it_setup"},
    {"id": "flow_3", "from": "gateway_parallel_start", "to": "task_hr_paperwork"},
    {"id": "flow_4", "from": "task_it_setup", "to": "gateway_parallel_join"},
    {"id": "flow_5", "from": "task_hr_paperwork", "to": "gateway_parallel_join"},
    {"id": "flow_6", "from": "gateway_parallel_join", "to": "task_next"}
  ]
}
```

---

## 4. 承認プロセスの標準パターン

承認プロセスは「承認作業（タスク）」と「承認結果の分岐（ゲートウェイ）」を組み合わせて表現します。

### パターン1: 単純承認フロー

```
[申請書作成] → [上長承認] → [承認結果分岐] → [承認: 次工程 / 却下: 差戻し]
   (タスク)      (タスク)     (ゲートウェイ)
```

### パターン2: 条件付き承認フロー

```
[申請書作成] → [金額判定] → [10万円以上: 部長承認 / 10万円未満: 自動承認]
   (タスク)   (ゲートウェイ)
```

### パターン3: 多段承認フロー

```
[申請] → [課長承認] → [承認?] → [YES: 部長承認] → [承認?] → [YES: 次工程]
                              ↓ NO                      ↓ NO
                           [差戻し]                   [差戻し]
```

---

## 5. システム自動処理の表現

システムによる自動処理は、その性質に応じてタスクまたはゲートウェイで表現します。

### 5.1 システムがデータ処理を行う場合 → タスク

```json
{
  "id": "task_auto_validation",
  "name": "入力データ自動検証",
  "actor_id": "actor_system",
  "notes": "システムがデータ形式・必須項目を検証"
}
```

### 5.2 システムが条件判定を行う場合 → ゲートウェイ

```json
{
  "id": "gateway_auto_check",
  "name": "在庫有無判定",
  "type": "exclusive",
  "notes": "システムが在庫DBを確認し分岐"
}
```

### 5.3 ルール: 「システムが○○する」の判断基準

| 内容 | 分類 | 例 |
|------|------|-----|
| システムがデータを加工・保存・送信する | タスク | データ変換、DB保存、メール送信 |
| システムが条件を評価して分岐する | ゲートウェイ | 在庫判定、権限チェック、閾値判定 |

---

## 6. まとめ: 黄金ルール

1. **実作業はタスク、判定・分岐はゲートウェイ**
2. **タスクとゲートウェイを重複させない**（同じ名前で両方定義しない）
3. **ゲートウェイには必ず2つ以上の出力フローが必要**
4. **承認行為は「承認タスク + 結果判定ゲートウェイ」の組み合わせ**
5. **並行処理は並行ゲートウェイ (parallel) で表現**
6. **システム自動判定はゲートウェイで表現**

---

## 7. 参考資料

- [BPMN 2.0 仕様](https://www.omg.org/spec/BPMN/2.0/)
- [BPMN Gateway Types Explained](https://www.bpmn.org/)

---

## 8. 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| v1.0 | 2025-11-12 | 初版作成（タスクとゲートウェイの概念定義、使い分けガイドライン、誤用パターン、標準パターン） |
