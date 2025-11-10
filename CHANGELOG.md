# CHANGELOG

[最終更新日時] 2025年11月10日 13:06 JST

本ファイルは Business-flow-maker プロジェクトの全ての重要な変更を記録します。

## バージョン採番ルール

- **形式**: `v0.x` (MVP開発中は 0.x 系列)
- **インクリメント**: 機能追加・構造変更ごとにマイナーバージョン (x) を +1
- **Hotfix**: 小数点2桁 (例: v0.31)
- **v1.0.0 以降**: セマンティックバージョニング (major.minor.patch) を採用予定

## 履歴（昇順: 古い順）

---

### [v0.1] - 2025-11-07 22:50 JST

#### 追加
- プロジェクト初版の作成
- **PLAN.md** 初稿（開発計画書）
- 基本的なディレクトリ構造の確立

---

### [v0.2] - 2025-11-08 00:12 JST

#### 追加
- UTF-8 正常化処理
- ディレクトリ雛形の作成（src/layer1, src/layer2, src/export, schemas/, samples/）
- サンプル3件追加（small/medium/large）
- JSON Schema 草案の作成 (schemas/flow.schema.json)
- Layer1 ジェネレーター雛形の実装

---

### [v0.3] - 2025-11-08 14:02 JST

#### 追加
- **requirements.txt** を追加
- 環境セットアップ手順を PLAN.md に追記
- 仮想環境 (.venv) による依存管理

---

### [v0.31] - 2025-11-08 17:07 JST

#### 修正（Hotfix）
- **Layer1可視化Hotfix**: HTML/SVG/レビュー出力をUTF-8(BOM付)に統一
- Swimlane配置を補正（レーン中央整列）
- Windows ローカル閲覧での文字化け対策

---

### [v0.32] - 2025-11-08 23:49 JST

#### 追加
- LLM プロバイダ自動検出機能 (Azure OpenAI / OpenAI 自動切り替え)
- generation メタデータの追記機能（モデル名、プロバイダ情報）
- **.env.example** を追加（環境変数テンプレート）

---

### [v0.33] - 2025-11-10 02:40 JST

#### 追加
- **src/llm_client_builder.py** を新規作成（LLMクライアント関連機能を分離）
- **src/export/mermaid_generator.py** を新規作成（flow.json → Mermaid flowchart TD変換）
- **samples/input/sample-tiny-01.md** と **samples/expected/sample-tiny-01.json** を追加
  - 備品購入申請フロー：2部署、7タスク、1ゲートウェイ

#### 変更
- **src/layer1/generator.py** → **src/layer1/flow_json_generator.py** にリネーム

---

### [v0.34] - 2025-11-10 10:12 JST

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

### [v0.35] - 2025-11-10 10:23 JST

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

### [v0.36] - 2025-11-10 13:06 JST

#### 修正
- **src/core/generator.py の文字化けバグ修正**
  - build_prompt() 関数内のプロンプト文字列が文字化けしていた問題を修正
  - UTF-8で正しく読める日本語プロンプトに変更
  - 内容：業務フローアーキテクトとして、JSON生成の必須ルールを指示

#### 変更
- **PLAN.md の全面再構成**
  - §0〜§12 構成から §1〜§10 の新構成へ移行
  - §1. プロジェクト概要（背景・目的、入出力、技術方針）
  - §2. アーキテクチャ（二層構成、機能/非機能要件）
  - §3. スコープ管理（MVP完了項目、将来検討項目）
  - §4. 開発環境（セットアップ、LLMプロバイダ自動検出、実行例）
  - §5. 実行履歴管理（runs/構造の詳細仕様）
  - §6. 実装ロードマップ（完了済み、次ステップ、将来計画）
  - §7. 標準運用フロー
  - §8. 品質保証（テスト、検証、KPI）
  - §9. リスクと対策
  - §10. 変更管理ポリシー

#### 追加
- **§4.2**: LLMプロバイダ自動検出方式の詳細
  - 単一 .env ファイル運用
  - Azure優先、OpenAI APIフォールバック
  - ダミー値自動無効化
- **§5**: runs/ 構造の完全な仕様
  - ディレクトリ命名規則（YYYYMMDD_HHMMSS_{input_stem}）
  - info.md の記録内容
  - 入力ファイルコピーとSHA-256ハッシュ
- **§6.1**: 完了済み機能の明記
  - Layer1 MVP完成
  - runs/ 構造導入
  - LLMプロバイダ自動検出
- **§9.2**: プロバイダ検出失敗時の対応
- **§9.3**: runs/ ディレクトリクリーンアップ推奨

#### 削除
- §4.x の手動 .env 切り替え方式の記述（.env.openai / .env.azure コピー操作）
- 古いパス名（src/layer1/generator.py）
- Phase 0〜4 の詳細な実装ステップ説明（§6に集約）

#### ドキュメント
- §1.3: 「ユーザーへプロバイダ選択を促し」→「環境変数から自動検出」に修正
- §2.1: 実装構造を src/core/, src/visualizers/, src/utils/ に更新
- §3.1: MVP完了項目に runs/ 構造と自動検出を追加
- §7: 運用フローを runs/ 構造ベースに全面改訂

---

_※ 今後の開発計画については [PLAN.md](PLAN.md) を参照してください。_
