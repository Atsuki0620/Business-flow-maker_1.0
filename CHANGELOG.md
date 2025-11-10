# CHANGELOG

本ファイルは Business-flow-maker プロジェクトの全ての重要な変更を記録します。

## バージョン採番ルール

- **形式**: `v0.x` (MVP開発中は 0.x 系列)
- **インクリメント**: 機能追加・構造変更ごとにマイナーバージョン (x) を +1
- **Hotfix**: 小数点2桁 (例: v0.31)
- **v1.0.0 以降**: セマンティックバージョニング (major.minor.patch) を採用予定

## 履歴（昇順: 古い順）

---

### [v0.1] - 2025-11-07 22:50

#### 追加
- プロジェクト初版の作成
- **PLAN.md** 初稿（開発計画書）
- 基本的なディレクトリ構造の確立

---

### [v0.2] - 2025-11-08 00:12

#### 追加
- UTF-8 正常化処理
- ディレクトリ雛形の作成（src/layer1, src/layer2, src/export, schemas/, samples/）
- サンプル3件追加（small/medium/large）
- JSON Schema 草案の作成 (schemas/flow.schema.json)
- Layer1 ジェネレーター雛形の実装

---

### [v0.3] - 2025-11-08 14:02

#### 追加
- **requirements.txt** を追加
- 環境セットアップ手順を PLAN.md に追記
- 仮想環境 (.venv) による依存管理

---

### [v0.31] - 2025-11-08 17:07

#### 修正（Hotfix）
- **Layer1可視化Hotfix**: HTML/SVG/レビュー出力をUTF-8(BOM付)に統一
- Swimlane配置を補正（レーン中央整列）
- Windows ローカル閲覧での文字化け対策

---

### [v0.32] - 2025-11-08 23:49

#### 追加
- LLM プロバイダ自動検出機能 (Azure OpenAI / OpenAI 自動切り替え)
- generation メタデータの追記機能（モデル名、プロバイダ情報）
- **.env.example** を追加（環境変数テンプレート）

---

### [v0.33] - 2025-11-10 02:40

#### 追加
- **src/llm_client_builder.py** を新規作成（LLMクライアント関連機能を分離）
- **src/export/mermaid_generator.py** を新規作成（flow.json → Mermaid flowchart TD変換）
- **samples/input/sample-tiny-01.md** と **samples/expected/sample-tiny-01.json** を追加
  - 備品購入申請フロー：2部署、7タスク、1ゲートウェイ

#### 変更
- **src/layer1/generator.py** → **src/layer1/flow_json_generator.py** にリネーム

---

### [v0.34] - 2025-11-10 10:12

#### 追加
- **README.md** を新規作成
  - プロジェクト概要、インストール手順、クイックスタート
- **CHANGELOG.md** を新規作成（本ファイル、v0.1～v0.33の改訂履歴を移行）

#### 変更
- **PLAN.md** の改訂履歴セクションを全て削除し、CHANGELOG.mdへ移行
- **PLAN.md** の§13「直近の実装状況」、§14「直近タスク計画」を削除
- **PLAN.md** に目標ディレクトリ構造（src/core/visualizers/utils/）を追記
- **AGENTS.md** の必読ドキュメントセクションを更新（README.md優先）

#### 削除
- **output/README.md** を削除（将来runs/構造へ移行）

---

### [v0.35] - 2025-11-10 10:23

#### 追加
- **runs/構造導入**: 実行履歴の自動管理機能
  - タイムスタンプ付き実行ディレクトリ（`runs/YYYYMMDD_HHMMSS_{input_stem}/`）
  - info.md による実行情報記録（実行コマンド、入力情報、生成設定、JSON検証結果、レビューチェックリスト）
  - 入力ファイルの自動コピー（再現性確保）
- **src/utils/run_manager.py**: runs/構造管理機能
  - create_run_dir(): 実行ディレクトリ作成
  - copy_input_file(): 入力ファイルコピー
  - save_info_md(), update_info_md(): info.md生成・更新
  - get_latest_run(), list_runs(): 実行履歴取得

#### 変更
- **src/構造変更**: layer1/layer2/export → core/visualizers/utils/
  - `src/layer1/flow_json_generator.py` → `src/core/generator.py`
  - `src/llm_client_builder.py` → `src/core/llm_client.py`
  - `src/export/visualizer.py` → `src/visualizers/html_visualizer.py`
  - `src/export/mermaid_generator.py` → `src/visualizers/mermaid_visualizer.py`
- **generator.py**: --output オプションをデフォルトNoneに変更（省略時はruns/に自動生成）
- **html_visualizer.py**: runs/構造を検出してinfo.mdを更新
- **mermaid_visualizer.py**: runs/構造を検出してinfo.mdを更新
- **テストファイル**: 全importパスを新構造に更新

#### 削除
- **output/ディレクトリ**: runs/構造へ完全移行
- **review_checklist.txt**: info.mdに統合
- **build_review()関数**: html_visualizer.pyから削除
- **--review引数**: html_visualizer.pyから削除
- **旧ディレクトリ**: src/layer1/, src/layer2/, src/export/ を削除

#### ドキュメント
- README.md: runs/構造の説明とコマンド例を追加
- PLAN.md: §11「成果物・保管方針」にruns/構造を追記
- importパスを全て新構造に更新

#### 後方互換性
- --output オプション指定で従来通りの動作を維持

#### 修正
- パス相対化処理の修正 (v0.35.1 相当)
  - html_visualizer.py と mermaid_visualizer.py で相対パスと絶対パスの混在によるエラーを修正
  - resolve() で絶対パスに統一してから相対化処理

---

_※ 今後の開発計画については [PLAN.md](PLAN.md) を参照してください。_
