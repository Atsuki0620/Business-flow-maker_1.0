# CHANGELOG

本ファイルは Business-flow-maker プロジェクトの全ての重要な変更を記録します。

---

## [v0.34] - 2025-11-10

### 追加
- **README.md** を新規作成（プロジェクト概要、インストール手順、クイックスタート）
- **CHANGELOG.md** を新規作成（v0.1～v0.33の改訂履歴を移行）

### 変更
- **PLAN.md** の改訂履歴セクションを全て削除し、CHANGELOG.mdへ移行
- **PLAN.md** の§13「直近の実装状況」、§14「直近タスク計画」を削除
- **PLAN.md** に目標ディレクトリ構造（src/core/visualizers/utils/）を追記
- **AGENTS.md** の必読ドキュメントセクションを更新（README.md優先）

### 削除
- **output/README.md** を削除（将来runs/構造へ移行）

### 備考
- ドキュメント構成を整理し、プロジェクト構造の移行準備を完了

---

## [v0.33] - 2025-11-10

### 追加
- **src/llm_client_builder.py** を新規作成（LLMクライアント関連機能を分離）
- **src/export/mermaid_generator.py** を新規作成（flow.json → Mermaid flowchart TD変換）
- **samples/input/sample-tiny-01.md** と **samples/expected/sample-tiny-01.json** を追加（備品購入申請フロー：2部署、7タスク、1ゲートウェイ）

### 変更
- **src/layer1/generator.py** → **src/layer1/flow_json_generator.py** にリネーム

---

## [v0.32] - 2025-11-08

### 追加
- LLM プロバイダ自動検出機能
- generation メタデータの追記機能
- **.env.example** を追加（環境変数テンプレート）

---

## [v0.31] - 2025-11-08

### 修正
- **Layer1可視化Hotfix**: HTML/SVG/レビュー出力をUTF-8(BOM付)に統一
- Swimlane配置を補正（レーン中央整列）

---

## [v0.3] - 2025-11-08

### 追加
- **requirements.txt** を追加
- 環境セットアップ手順を PLAN.md に追記

---

## [v0.2] - 2025-11-07

### 追加
- UTF-8 正常化処理
- ディレクトリ雛形の作成
- サンプル3件追加（small/medium/large）
- JSON Schema 草案の作成
- Layer1 ジェネレーター雛形の実装

---

## [v0.1] - 2025-11-07

### 追加
- プロジェクト初版の作成
- **PLAN.md** 初稿（開発計画書）
- 基本的なディレクトリ構造の確立

---

## 直近タスク進捗

### PDCA①: 環境整備
- **Status**: ✅ 完了（2025-11-08）
- **実施内容**:
  - `.venv` 仮想環境の作成
  - `requirements.txt` に依存パッケージ記載
  - `.env` による API キー読み込み機能
  - Stub/本番 API での動作確認
- **次のステップ**: README 反映と CI 手順整備

### PDCA②: Layer1 自動テスト拡充
- **Status**: ✅ 完了（2025-11-08）
- **実施内容**:
  - `tests/conftest.py` と `tests/test_layer1_generator.py` を追加
  - pytest で3ケースが通過
- **次のステップ**: CI 追加と LLM 実行パスのモック化

### PDCA③: Layer2/BPMN パイプライン実装
- **Status**: 🚧 未着手
- **予定内容**:
  - JSON→BPMN 変換モジュールの実装
  - bpmnlint 連携
  - SVG/PNG エクスポート手順の定義

---

## 次期予定: v0.35（準備中）

### 予定内容
- **src/構造変更**: layer1/layer2/export → core/visualizers/utils/
- **runs/構造導入**: 実行履歴の自動管理機能
- **info.md**: 各実行の詳細情報記録
- **output/削除**: runs/構造への完全移行
- **review_checklist.txt削除**: info.mdに統合
