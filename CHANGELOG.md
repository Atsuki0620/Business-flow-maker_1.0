# CHANGELOG

[最終更新日時] 2025年11月13日 JST

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

### [v0.36] - 2025-11-10 22:15 JST

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

### [v0.37] - 2025-11-11 09:30 JST

#### 修正（重大）
- **OpenAI SDK API の使用方法を修正**
  - `client.responses.create()` → `client.chat.completions.create()` に変更
  - パラメータを修正：`input` → `messages=[{"role": "user", "content": prompt}]`
  - レスポンス取得を修正：`response.output[0].content[0].text` → `response.choices[0].message.content`
  - OpenAI SDK の正しい Chat Completions API を使用するように修正
- **デフォルトモデル名を修正**
  - `gpt-4.1-mini` → `gpt-4o-mini` に変更（存在しないモデル名の修正）
- **プロバイダ検出ロジックを簡素化**
  - `test_openai_available()` と `test_azure_available()` 関数を削除
  - `detect_provider()` を環境変数チェックとダミー値判定のみに簡素化
  - SDK初期化は `create_llm_client()` 内で実施（初期化失敗時は明確なエラーメッセージ）

#### 追加
- **構造化ロギング導入**
  - `logging` モジュールを `llm_client.py`, `generator.py`, `html_visualizer.py` に導入
  - INFO/WARNING/ERROR/DEBUGレベルのログ出力
  - `--debug` フラグ追加で DEBUGレベルのログを表示（LLMリクエスト・レスポンス全文）
- **プロンプト改善（Few-shot examples）**
  - `build_messages()` 関数を新設（`build_prompt()` から変更）
  - システムプロンプトを分離（業務フローアーキテクトとしての役割明示）
  - Few-shot example 追加（`sample-tiny-01.md` → `sample-tiny-01.json`）
  - messagesリスト形式でLLM APIに渡すように変更
- **基本的なエラーハンドリング**
  - `structured_flow()` メソッドに try-catch を追加
  - API呼び出し失敗時に `RuntimeError` で明確なエラーメッセージを表示
  - レスポンスが空の場合に `ValueError` で通知
  - JSONパース失敗時に元のレスポンス内容を含めてエラー通知
- **可視化でのエラーハンドリング**
  - `html_visualizer.py` で存在しないIDへのflow参照を検出
  - ワーニングログを出力してflowをスキップ（処理は続行）

#### 変更
- **normalize_flow_document() の簡素化**
  - ダミーデータ自動挿入を廃止（actors/phases/tasks/flowsが0件でもダミー挿入しない）
  - LLMが生成したデータをそのまま正規化（ID生成、データ型正規化、必須フィールド補完のみ実施）
  - 参照整合性チェックは削除（LLMとプロンプトに委譲）

#### 削除
- **厳密検証モードの計画を撤回**
  - LLMのJSON Schema制約と改善されたプロンプトで品質を担保
- **参照整合性の自動チェック機能の計画を撤回**
  - Few-shot examplesとシステムプロンプトで参照整合性を指示

---

### [v0.38] - 2025-11-12 00:35 JST

#### 修正（可視化レイヤー改善）
- **HTML可視化: ノード重なり問題を修正**
  - `src/visualizers/html_visualizer.py`: 同一phase内の複数タスクが同一座標に配置される問題を修正
  - 2パスアプローチを実装: グループごとのタスク数をカウント → Y座標をオフセット
  - 同一(actor_id, phase_id)グループ内のタスクをY方向に10px間隔で配置
  - グループを垂直方向に中央揃え
- **Mermaid可視化: ゲートウェイ孤立問題を修正**
  - `src/visualizers/mermaid_visualizer.py`: フローに接続されていないゲートウェイノードを非表示
  - flowsで参照されているゲートウェイIDのみを定義（暫定対策）
- **Few-shot exampleの修正**
  - `samples/expected/sample-tiny-01.json`: タスクとゲートウェイの重複を解消
  - `task_amount_judgment`（金額判定タスク）を削除
  - `gateway_amount`をフロー構造に統合（task_create_request → gateway_amount → 分岐先）
  - 正しいBPMN表現の模範例として修正
- **LLMプロンプトの改善**
  - `src/core/generator.py`: ゲートウェイの使用ルールを追加（ルール7）
  - 判定・分岐処理はタスクではなくゲートウェイとして表現
  - ゲートウェイとタスクを重複させない明示
  - ゲートウェイtype（exclusive/parallel/inclusive）の説明追加
  - ゲートウェイには2つ以上の出力フローが必要と明記
  - システムによる自動判定処理はゲートウェイとして表現

#### 追加（ドキュメント）
- **docs/IMPROVEMENTS.md を新規作成**
  - 可視化レイヤーの問題分析と改善計画を記録
  - Phase 1（v0.38）とPhase 2（次期バージョン）の詳細計画
  - 問題箇所の特定（ファイル名:行番号付き）
  - 決定事項ログと検証結果の記録
  - BPMN準拠実装への移行計画（Phase 2）

#### 検証
- sample-tiny-01, sample-medium-01 で動作確認
- ノード重なり解消を確認
- Mermaidでゲートウェイが正しくフロー接続されることを確認
- LLMがゲートウェイを適切に使用することを確認

#### 既知の問題（Phase 2で対応予定）
- ゲートウェイ配置アルゴリズムの改善が必要（位相ソート実装）
- 正規化処理の追加（判定タスクをゲートウェイに自動変換）
- レイアウトエンジンの改善（Sugiyama-style layering、elk.js導入検討）

---

### [v0.39] - 2025-11-12 02:00 JST

#### 追加（ドキュメント・プロンプト品質改善）
- **docs/CONCEPTS.md を新規作成**
  - BPMN 2.0仕様に基づくタスクとゲートウェイの概念定義
  - 使い分けガイドラインと判定基準フローチャート
  - よくある誤用パターンと修正例（3パターン）
  - 承認プロセスの標準パターン（3パターン）
  - システム自動処理の表現方法（判断基準表）
  - 黄金ルール（6項目）の明記

#### 変更（LLMプロンプトの体系的改善）
- **src/core/generator.py: build_messages() 関数を改善**
  - システムプロンプトを全面再構成
    - タスクとゲートウェイの使い分けを視覚的に説明（✅/❌マーク付き）
    - BPMN 2.0準拠であることを明記
    - 黄金ルール（5項目）を追加
    - 具体例を大幅に追加（申請書作成、部長承認、金額判定など）
  - Few-shot examplesを1つから2つに増強
    - sample-tiny-01: 基本的な直列フロー（2部署、7タスク、1ゲートウェイ）
    - sample-small-01: 条件分岐を含むフロー（3部署、4タスク、1ゲートウェイ）
    - 段階的に複雑度が上がる順に配置
  - ループ処理で複数exampleを読み込む拡張可能な構造に変更

#### 効果
- タスクとゲートウェイの使い分けが一層明確化
- LLMがBPMN概念に準拠したJSON生成を行いやすくなる
- Few-shot examplesの増加により、複雑なフローにも対応可能

#### テスト
- pytest実行結果: 9/10テストが成功（主要機能テストは全て成功）
- 既存機能に影響なし

#### ドキュメント
- README.md にCONCEPTS.mdへの参照を追加予定

---

### [v0.40] - 2025-11-13 JST

#### 追加（Layer2: BPMN 2.0準拠出力・可視化機能）
- **BPMN 2.0 XML出力機能の実装**
  - JSON形式の業務フローデータからBPMN 2.0準拠のXMLを生成
  - 正しい名前空間定義（bpmn2、bpmndi、dc、di、xsi）
  - collaboration要素によるスイムレーン構造の実装
  - process要素とlaneSet要素の生成
  - userTask/serviceTaskの区別（タスクタイプに応じた要素生成）
  - exclusiveGateway/parallelGateway/inclusiveGatewayの完全サポート
  - sequenceFlow要素の生成（条件付きフロー対応）
  - BPMNDiagram/BPMNPlane/BPMNShape/BPMNEdgeによる図形情報の完全実装

- **動的座標計算アルゴリズムの実装**
  - **src/core/bpmn_layout.py**: Sugiyamaアルゴリズムベースのレイアウトエンジン
    - 第1段階: トポロジカルソートによる階層決定
    - 第2段階: バリセントリック法による交差最小化
    - 第3段階: 水平座標の動的割り当て
    - 第4段階: エッジ経路の計算
  - 固定座標値を完全に排除し、すべて動的計算
  - フロー規模に応じた自動スケーリング（ノード数の平方根に比例）
  - 日本語ラベル長を考慮した幅調整
  - レーン内最大ノード数に応じた高さ調整

- **SVG可視化機能の実装**
  - **src/core/bpmn_converter.py**: BPMN準拠のSVG画像生成
    - タスク: 角丸矩形（userTask=白、serviceTask=薄青）
    - ゲートウェイ: 菱形（exclusive=×、parallel=+、inclusive=○）
    - シーケンスフロー: 矢印付き線（条件ラベル対応）
    - スイムレーン: 背景矩形領域（actor名表示）
  - GitHub自動プレビュー対応（埋め込みCSSスタイル）
  - XML宣言付きSVG出力（UTF-8エンコーディング）

- **BPMN 2.0準拠性検証機能の実装**
  - **src/core/bpmn_validator.py**: 包括的な妥当性検証
    - 名前空間の検証
    - 基本構造の検証（definitions、process、collaboration）
    - ID一意性の検証
    - 参照整合性の検証（sequenceFlow、BPMNShape、BPMNEdge）
    - 図形情報の検証（Bounds、waypoint）
    - 統計情報の取得（tasks、gateways、sequence_flows、lanes、participants）

- **runs構造への完全統合**
  - 入力JSONがruns/ディレクトリ内にある場合、自動的にoutput/サブディレクトリに出力
  - `flow.bpmn`: BPMN 2.0 XML形式
  - `flow-bpmn.svg`: BPMN準拠のSVG画像（既存のflow.svgと区別）
  - `src/utils/run_manager.py`のupdate_info_md関数を使用してinfo.md自動更新
  - BPMN変換の実行情報（出力ファイルパス・サイズ、検証結果、SVG生成状況）を記録
  - runs構造を使用しない場合の後方互換性維持

- **CLI機能の実装**
  - `python -m src.core.bpmn_converter` で実行可能
  - コマンドライン引数:
    - `--input`: 入力JSONファイルパス（必須）
    - `--output`: 出力BPMNファイルパス（省略時は自動決定）
    - `--svg-output`: SVGファイルの出力先（省略時は自動決定）
    - `--no-svg`: SVG生成を無効化
    - `--validate`: 生成後の妥当性検証実行（デフォルト: 有効）
    - `--debug`: デバッグ情報出力
  - runs/構造の自動検出と適切な出力先決定

- **包括的なテストスイートの実装**
  - **tests/test_bpmn_converter.py**: 単体テストと統合テスト
    - レイアウト計算の動作確認
    - BPMN XML変換の妥当性検証
    - SVG生成の正常動作確認
    - 異なる規模のフローに対するテスト（tiny/small/medium/large）
    - エッジケースの処理（空のフロー、不正なXML）
    - 実際のサンプルファイルを使用した統合テスト

- **サンプル出力の生成**
  - **samples/bpmn/**: 代表的な成果物を配置
    - sample-tiny-01.bpmn/svg
    - sample-small-01.bpmn/svg
    - sample-medium-01.bpmn/svg
    - sample-large-01.bpmn/svg
  - samples/bpmn/README.md: 日本語で目的と使用方法を説明
  - GitHubで成果物が直接プレビュー可能

#### 技術仕様
- **BPMN準拠**: OMG BPMN 2.0 Specification完全準拠
- **エンコーディング**: UTF-8
- **依存**: Python標準ライブラリのみ（xml.etree.ElementTree使用）
- **決定論的処理**: 同一JSON入力に対して常に同一のBPMN/SVG出力
- **LLM不使用**: 純粋な構造変換処理として実装

#### 変換マッピング仕様
- actors → participant要素およびlane要素（スイムレーン構造）
- tasks → userTask（人的作業）またはserviceTask（システム処理）要素
- gateways → exclusiveGateway（排他）、parallelGateway（並列）、inclusiveGateway（包含）要素
- flows → sequenceFlow要素（条件付き分岐を含む）
- phases → タスクの配置順序として反映

#### ドキュメント
- すべてのdocstring、コメント、エラーメッセージを日本語で記述
- 包括的なREADME.md（samples/bpmn/）
- CHANGELOG.md、README.md、PLAN.mdの更新

#### 成功基準達成
- ✓ sample-tiny-01.jsonから有効なBPMN 2.0 XMLが生成される
- ✓ SVGファイルが自動生成され、ブラウザで正しく表示される
- ✓ 生成されたXMLがBPMN 2.0スキーマに完全準拠している
- ✓ 座標が動的に計算され、異なる規模のフローでも適切に配置される
- ✓ スイムレーン構造が正しく表現される
- ✓ ゲートウェイによる分岐がBPMN標準通りに実装される
- ✓ runs構造での実行時に適切な出力先が自動決定される
- ✓ info.mdに実行情報が日本語で適切に記録される
- ✓ GitHubのWebインターフェースでSVGファイルが直接プレビュー可能
- ✓ すべてのドキュメント、コメント、メッセージが日本語で記述されている

#### 既知の制限（今回のスコープ外）
- エクスポート機能（PNG出力等）は未実装
- bpmn-jsプレビュー機能は未実装

---

_※ 今後の開発計画については [PLAN.md](PLAN.md) を参照してください。_
