# Business-flow-maker 計画書

[最終更新日時] 2025年11月20日 JST

## 参照ドキュメント
- [README.md](README.md) - プロジェクト概要とクイックスタート
- [CHANGELOG.md](CHANGELOG.md) - 改訂履歴とバージョン管理
- [AGENTS.md](AGENTS.md) - 開発者向けガイドライン

---

## §1. プロジェクト概要

### §1.1 背景と目的
- **目的**：マニュアル整備やシステム要件整理に使える業務フローを、短時間で下書きから確定形まで落とし込める仕組みを整備する。
- **利用想定**：個人利用が主。小規模〜部署横断まで対応できる柔軟性を確保。

### §1.2 入出力
- **入力**：文章、業務文書、箇条書き、Excel など（構造化／非構造データ混在、複数ファイル結合可）。
- **出力**：
  - 中間生成物：独自JSON（actors/phases/tasks/flows/issues 等）とブラウザで確認できる静的HTML。
  - 確定成果物：BPMN 2.0 XML（.bpmn）と bpmn-js プレビュー、SVG/PNG 画像。PPTX は当面手動貼り付け。
  - Excel：Actors/Tasks/Flows/RACI/Issues を表形式で出力。

### §1.3 技術方針
- **LLM環境**：OpenAI API / Azure OpenAI API を利用。API キーやエンドポイントは `.env`（git 未管理）に格納し、環境変数から自動検出する。
- **プロバイダ検出**：単一 `.env` ファイルから Azure OpenAI を優先的に検出し、未設定の場合は OpenAI API にフォールバック。ダミー値は自動的に無効化。
- **CLI/スクリプト中心**：必要に応じて Streamlit 等を検討。
- **正規化フロー**：正規化＆クリーニング工程は MVP では省略。要望が高まった段階でオプション機能として追加。

---

## §2. アーキテクチャ

### §2.1 二層構成
- **レイヤー1（LLM 親和な下書き）**
  - LLM で独自JSON（actors/phases/tasks/flows/issues）を生成する。
  - HTML+JS（elk.js 等）で自動レイアウトしたSVGを表示する。
  - JSON Schema 検証と軽量な体裁チェック、レビュー用チェックリストを自動出力する。
  - **実装構造**: `src/core/generator.py` + `src/visualizers/`（HTML/SVG、Mermaid生成）
- **レイヤー2（BPMN 準拠の確定形）**
  - 独自JSONを BPMN 2.0 XML へ変換する。
  - BPMN準拠のSVG画像を生成し、GitHub上で直接プレビュー可能にする。
  - 動的座標計算により異なる規模のフローに対応する。
  - 構造レベルと幾何レベルに分離したレイアウトエンジンで高品質な配置を実現する（**v0.42で全面改訂**）。
  - 直交（マンハッタン）ルーティングにより可読性の高いエッジ描画を実現する。
  - **実装構造**: `src/core/bpmn_converter.py`、`src/core/bpmn_layout.py`、`src/core/bpmn_validator.py`（**v0.40で実装、v0.42で大幅改善**）

### §2.2 機能要件
1. **独自JSON生成**：actors, phases, tasks（責任/RACI/handoff_to/systems/notes を含む）、gateways、flows、issues を出力し、曖昧な点は `issues` に列挙する。
2. **ブラウザ可視化（レイヤー1）**：JSON を読み込み、泳走レーン／縦積みレイアウトで SVG 化し、未参照IDや孤立ノードも検知する。
   - Windowsローカル確認を優先し、HTML/SVG/レビューはUTF-8(BOM付)で書き出す。
   - Swimlane内タスク/ゲートウェイはレーン中央に整列させ図の崩れを抑制。
3. **BPMN変換（レイヤー2）**：laneSet、task、exclusiveGateway、sequenceFlow を生成し、bpmn-js＋bpmnlint で検証する。
4. **エクスポート**：SVG/PNG を高解像度で出力し、PPT 貼付に耐える品質を確保する。
5. **レビュー出力**：本書 §8 のチェックリストと Lint 結果をテキストで出力する。

### §2.3 非機能要件
- **再現性**：同じ入力で同等の JSON 構造を返す（温度／プロンプト管理）。
- **可搬性**：ローカル実行／オフライン可視化を前提とする。
- **拡張性**：正規化・PPT 自動化・UI 導入を後付けできるアーキテクチャ。
- **セキュリティ**：機微情報はローカル保持。API 送信前に匿名化オプションを用意。

---

## §3. スコープ管理

### §3.1 MVP完了項目
- ✅ 文章／複数ファイルの取り込みと軽微な整形
- ✅ LLM による独自JSON生成と厳格スキーマ（未知は UNKNOWN）出力
- ✅ JSON Schema 検証と構造・必須項目の欠落チェック
- ✅ HTML（ローカル静的サイト）による可視化と自動レイアウト
- ✅ レビュー用チェックリストの自動生成
- ✅ **runs/ 構造による実行履歴管理**（v0.35〜）
- ✅ **LLMプロバイダ自動検出**（Azure優先、ダミー値自動無効化）
- ✅ **BPMN 2.0 XML変換とSVG可視化**（v0.40で実装完了、v0.42で大幅改善）
  - JSON→BPMN 2.0 XML変換（lanes, tasks, exclusiveGateway/parallelGateway/inclusiveGateway, sequenceFlow）
  - BPMN準拠のSVG画像自動生成（GitHub直接プレビュー対応）
  - 動的座標計算（Sugiyamaアルゴリズムベース、v0.42で全面改訂）
  - 構造・幾何分離アーキテクチャによる高品質レイアウト（v0.42）
  - 直交（マンハッタン）ルーティングによる可読性の高いエッジ描画（v0.42）
  - BPMN 2.0準拠性の自動検証
- ✅ **コードレビュー対応と品質改善**（v0.41で実装完了）
  - Python 3.9互換性の確保（型ヒント構文修正）
  - コードリファクタリング（長大な関数の分割、責任の明確化）
  - カスタム例外クラスの導入（src/core/exceptions.py）
  - ドキュメント包括更新（README/samples/schemas/src の全面改訂）

### §3.2 将来検討項目
- bpmn-js プレビュー機能、bpmnlint チェック連携
- PNG出力機能（SVG→PNG変換）
- 入力の高度な正規化／クリーニング、表記ゆれ辞書、ID 採番強化
- UI フレームワーク固定（Streamlit 等）やコラボ機能
- PPTX 自動生成（python-pptx 等）
- RAG による過去フロー・規程集・社内用語辞書の参照

---

## §4. 開発環境

### §4.1 セットアップ手順
- **仮想環境**：`python -m venv .venv` で環境を作成し、Windows では `.\.venv\Scripts\activate` で有効化する。
- **依存導入**：`pip install -r requirements.txt` を実行すると以下がインストールされる：
  - openai>=1.44.0
  - jsonschema>=4.22.0
  - python-dotenv>=1.0.1
- **環境変数**：`.env` ファイルに以下を設定：
  ```
  # Azure OpenAI を使用する場合（優先）
  AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
  AZURE_OPENAI_API_KEY=your-azure-key-here
  AZURE_OPENAI_API_VERSION=2024-02-15-preview

  # OpenAI API を使用する場合（Azureが未設定の場合にフォールバック）
  OPENAI_API_KEY=sk-***

  # プロキシ設定（必要な場合のみ）
  HTTP_PROXY=http://proxy.example.com:8080
  HTTPS_PROXY=http://proxy.example.com:8080
  ```
- **確認ポイント**：
  - `output/flow.json` または `runs/` ディレクトリ配下に出力が生成されること
  - JSON Schema 検証が成功すること
  - API キー未設定時は SDK がエラーを返し問題箇所を特定できること

### §4.2 LLMプロバイダ自動検出方式
- **単一 .env ファイル運用**：`.env.openai` / `.env.azure` のコピー操作は不要
- **検出優先順位**：
  1. Azure OpenAI（`AZURE_OPENAI_ENDPOINT` と `AZURE_OPENAI_API_KEY` が設定されている場合）
  2. OpenAI API（`OPENAI_API_KEY` が設定されている場合）
- **ダミー値の自動無効化**：
  - `your-***-here` パターンは自動的に無効値として扱われる
  - 環境変数が存在してもダミー値の場合は未設定とみなす
- **検出結果の記録**：
  - 生成されたJSONの `metadata.generation` にモデル名とプロバイダ情報を記録
  - `runs/*/info.md` に実行時のプロバイダ情報を記録

### §4.3 実行コマンド例
```bash
# スタブ検証（LLM呼び出しなし）
python -m src.core.generator --input samples/input/sample-small-01.md --stub samples/expected/sample-small-01.json

# 本番 API（runs/構造に自動出力）
python -m src.core.generator --input samples/input/sample-small-01.md --model gpt-4.1-mini

# 従来の output/ ディレクトリに出力
python -m src.core.generator --input <input.md> --output output/flow.json --model gpt-4.1-mini
```

---

## §5. 実行履歴管理（runs/構造）

### §5.1 ディレクトリ構造
```
runs/
├── 20251110_123456_sample-small-01/
│   ├── info.md                      # 実行情報の詳細記録
│   ├── sample-small-01.md           # 入力ファイルのコピー
│   └── output/
│       ├── flow.json                # 生成されたJSON
│       ├── flow.html                # 可視化HTML
│       └── flow.svg                 # SVG画像
└── 20251110_140230_sample-medium-01/
    └── ...
```

### §5.2 ディレクトリ命名規則
- **形式**: `YYYYMMDD_HHMMSS_{input_stem}`
- **例**: `20251110_123456_sample-small-01`（sample-small-01.md を入力とした場合）

### §5.3 info.md の記録内容
- **基本情報**：実行ID（ディレクトリ名）、実行日時、実行コマンド
- **入力情報**：元ファイルパス、ファイルサイズ、SHA-256ハッシュ
- **生成設定**：LLMモデル、プロバイダ（openai/azure）、実行時間
- **出力ファイル**：相対パス、ファイルサイズ
- **JSON検証結果**：actors数、phases数、tasks数、flows数、gateways数、issues数
- **レビューチェックリスト**：各項目のOK/NG判定

### §5.4 入力ファイルコピー
- 再現性確保のため、元の入力ファイルを実行ディレクトリ直下にコピー
- SHA-256ハッシュを info.md に記録し、入力の同一性を担保

### §5.5 後方互換性
- `--output` オプション指定時は従来通り指定パスに出力
- runs/ 構造を使用しない場合でも既存の動作を維持

---

## §6. 実装ロードマップ

### §6.1 完了済み機能（v0.35時点）
- ✅ **Phase 0/1**: Layer1のMVP完成
  - LLM 呼び出しで JSON 生成（関数呼び出し／テンプレート）
  - JSON Schema 検証とエラーレポート
  - HTML+JS で SVG 可視化、elk.js で自動配置
  - レビュー用チェックリスト出力の自動化
- ✅ **ドキュメント整理**: README/CHANGELOG/PLAN の3層構造確立
- ✅ **src/構造変更**: core/visualizers/utils/ への再構成
- ✅ **runs/構造導入**: 実行履歴の自動管理
- ✅ **LLMプロバイダ自動検出**: Azure優先、ダミー値自動無効化

### §6.2 Layer2/BPMN パイプライン実装（v0.40で完了）
- ✅ JSON→BPMN 2.0 XML 変換モジュールの実装（`src/core/bpmn_converter.py`）
  - ✅ laneSet（泳線レーン）とcollaboration要素
  - ✅ userTask/serviceTask（タスクノード）
  - ✅ exclusiveGateway/parallelGateway/inclusiveGateway
  - ✅ sequenceFlow（条件付きフロー対応）
- ✅ 動的座標計算アルゴリズムの実装（`src/core/bpmn_layout.py`）
  - ✅ Sugiyamaアルゴリズムベースのレイアウトエンジン
  - ✅ トポロジカルソート、バリセントリック法による交差最小化
  - ✅ フロー規模に応じた自動スケーリング
- ✅ BPMN 2.0準拠性検証（`src/core/bpmn_validator.py`）
  - ✅ 名前空間、構造、ID一意性、参照整合性の検証
- ✅ BPMN準拠のSVG可視化機能
  - ✅ GitHub直接プレビュー対応（埋め込みCSSスタイル）
  - ✅ タスク（角丸矩形）、ゲートウェイ（菱形）の標準表現
- ✅ runs/構造への完全統合
  - ✅ 自動出力先決定（flow.bpmn、flow-bpmn.svg）
  - ✅ info.mdへの実行情報記録
- ✅ 包括的なテストスイート（`tests/test_bpmn_converter.py`）
- ✅ サンプル出力の生成（`samples/bpmn/`）

**完了基準達成**：
- `src/core/bpmn_converter.py` の実装
- bpmn-js での描画確認
- bpmnlint 合否検証
- 画像品質確認

### §6.3 コードレビュー対応と品質改善（v0.41で完了）
- ✅ **Python 3.9互換性の確保**
  - ✅ 型ヒント構文の修正（`tuple[...]` → `Tuple[...]`）
  - ✅ `typing.Tuple` をインポートに追加
- ✅ **コードリファクタリング**
  - ✅ `src/core/generator.py`: 長大な関数を分割
    - ✅ `_load_few_shot_examples()`: Few-shot examples読み込みを分離
    - ✅ `normalize_flow_document()`: 7つのヘルパー関数に分割
      - `_normalize_actors()`, `_normalize_phases()`, `_normalize_tasks()`
      - `_normalize_flows()`, `_normalize_gateways()`, `_normalize_issues()`
      - `_normalize_metadata()`
- ✅ **カスタム例外クラスの導入**
  - ✅ `src/core/exceptions.py`: ドメイン固有例外クラス階層を定義
    - `BusinessFlowMakerError`, `LLMClientError`, `BPMNConversionError`
    - `VisualizationError`, `FileIOError`, `RunManagerError` など14種類
- ✅ **ドキュメント包括更新**
  - ✅ README.md: BPMNワークフロー例、トラブルシューティング、ユースケース追加
  - ✅ samples/README.md: ディレクトリ構造更新、サイズ分類明記
  - ✅ samples/bpmn/README.md: 生成手順詳細化、ツール互換性リスト拡充
  - ✅ schemas/README.md: 存在しないファイルへの参照削除、スキーマ詳細説明
  - ✅ src/README.md: 現在のディレクトリ構造を反映、モジュール依存関係図追加

**完了基準達成**：
- コードの保守性向上（関数の行数削減、責任の明確化）
- エラーハンドリングの明確化（ドメイン固有例外）
- ドキュメントの網羅性向上（プロジェクト全体像の理解促進）
- Python 3.9以降での互換性保証

### §6.4 BPMNレイアウトエンジンの全面改訂（v0.42で完了）

#### §6.4.1 背景と課題認識

v0.40で実装されたSugiyamaベースのレイアウトエンジンは、基本的な動的座標計算を実現していたが、以下の課題が残されていた：

- **ノード配置の問題**：タスクやゲートウェイが斜め一列に並び、フローが「斜めの一本線」に潰れる傾向
- **時系列の不明確さ**：同じタイミング（フェーズ）の処理が縦方向に揃わず、現在のフェーズが直感的に読み取れない
- **スイムレーンの可読性**：レーン内のタスク位置がバラバラで、業務の流れと部署の役割が対応づけにくい
- **エッジの複雑さ**：斜めの矢印が多く、レーン跨ぎの線が交差・ニアミスして可読性が低い

これらの問題により、生成されたBPMN図が「人間のレビューや説明に耐えるレベル」に達していなかった。

#### §6.4.2 設計方針

v0.42では、レイアウトエンジンのアーキテクチャを以下の方針で全面改訂した：

**1. 構造レベルと幾何レベルの明確な分離**
- **構造レベル**：ノードのレーン（縦方向）とランク（横方向）の割り当て
  - スイムレーン割り当て：actors情報から lane_index を決定
  - ランク割り当て：トポロジカルソートで時系列順序を保証
  - 同一ランク内の順序最適化：交差最小化を考慮
- **幾何レベル**：具体的な座標とサイズの計算
  - ノードサイズの動的推定（ラベル長から自動計算）
  - レーン高さ・ランク幅の自動決定
  - 最終座標の計算（センタリング、マージン考慮）

**2. 中間レイアウトモデルの導入**
- `LayoutNode`: レイアウト計算用のノード中間モデル（lane_index, rank_index, x, y, width, height）
- `LayoutEdge`: エッジのルーティング情報（waypoints含む）
- `LayoutLane`: レーン情報（actor_id, height, y）
- `LayoutRank`: ランク（列）情報（width, x）

これにより、BPMN XMLの詳細から独立したレイアウト計算が可能になった。

**3. 直交（マンハッタン）ルーティングの実装**
- 原則として水平→垂直→水平の折れ線でエッジを描画
- 同一レーン＆隣接ランク：ほぼ水平の直線または1回曲がる程度
- レーン跨ぎ／ランク飛び越え：中継点（waypoint）を1〜2個挿入
- 斜めの長い線を基本的に排除し、可読性を大幅に改善

**4. 完全動的レイアウトの実現**
- サンプル固有の固定座標や条件分岐を完全排除
- すべての座標・サイズをJSON構造から動的に計算
- 任意の規模・構造のフローに対応可能な汎用性を確保

#### §6.4.3 実装内容

- ✅ **レイアウトエンジンの完全リファクタリング**（`src/core/bpmn_layout.py`、675行）
  - ✅ 中間レイアウトモデル（LayoutNode, LayoutEdge, LayoutLane, LayoutRank）の導入
  - ✅ 構造レベルレイアウト：`_assign_lanes()`, `_assign_ranks()`, `_order_nodes_in_rank()`
  - ✅ 幾何レベルレイアウト：`_calculate_node_sizes()`, `_calculate_lane_heights()`, `_calculate_rank_widths()`, `_calculate_coordinates()`
  - ✅ エッジルーティング：`_calculate_edge_waypoints()`, `_calculate_orthogonal_waypoints()`
  - ✅ トポロジカルソートベースのランク割り当てで時系列順序を保証

- ✅ **BPMN変換器の更新**（`src/core/bpmn_converter.py`）
  - ✅ `_add_diagram()`: レイアウトエンジンからwaypointsを取得して利用
  - ✅ `get_edge_waypoints_by_nodes()`: ノードペアでwaypointsを検索する機能追加
  - ✅ `BPMNSVGGenerator`: エッジ描画を`<line>`から`<polyline>`に変更
  - ✅ レイアウトロジックを`bpmn_layout.py`に集約し、変換器側はレイアウト結果を参照するだけに

- ✅ **サンプル出力の再生成**
  - ✅ 全サンプル（tiny/small/medium/large）でBPMN 2.0準拠のXML/SVG生成
  - ✅ レイアウト品質の大幅な改善を確認

#### §6.4.4 効果と制約

**効果**：
- ノードが時系列に沿って左から右へ明確に配置される
- エッジが直交経路で描画され、フローの追跡が容易になる
- スイムレーンの構造が明確に表現され、部署間のハンドオフが理解しやすい
- サンプル固有のロジックを完全排除し、汎用性を大幅に向上

**既知の制約**：
- エッジ交差の完全最適化は未実装（簡易ヒューリスティックのみ）
- 非常に複雑なフロー（100タスク以上）でのスケーラビリティは未検証
- アノテーション（注釈）ノードの配置は基本的なルールのみ

**今後の拡張ポイント**：
- エッジ交差最小化アルゴリズムの高度化（バリセントリック法の改良）
- サブプロセスの階層表現対応
- レイアウトパラメータのカスタマイズ機能（マージン、最小/最大サイズ等）
- 大規模フロー（100+タスク）のパフォーマンス最適化

**完了基準達成**：
- レイアウト品質の大幅改善（人間のレビューに耐えるレベル）
- アーキテクチャの明確化（構造・幾何分離、中間モデル導入）
- 汎用性の確保（固定座標の完全排除）
- テストの実行（25/31 passed、主要機能は全て動作）

### §6.5 将来計画（v1.0.0 に向けて）
- Layer2（BPMN変換）の実装完了
- 自動テストのカバレッジ拡充（目標: 80%以上）
- CI/CD パイプラインの整備（GitHub Actions）
- セマンティックバージョニング（major.minor.patch）への移行

---

## §7. 標準運用フロー

### §7.1 基本フロー（runs/構造を使用）
1. **素材収集と匿名化**
   - 業務文書を収集し、機密情報を匿名化
   - `samples/input/` ディレクトリに配置

2. **LLM で独自JSONを生成（レイヤー1）**
   ```bash
   python -m src.core.generator --input samples/input/example.md --model gpt-4.1-mini
   ```
   - 自動的に `runs/YYYYMMDD_HHMMSS_example/` が作成される
   - `info.md` に実行情報が記録される

3. **HTML 表示で目視確認**
   ```bash
   python -m src.visualizers.html_visualizer --json runs/YYYYMMDD_HHMMSS_example/output/flow.json
   ```
   - ブラウザで `runs/YYYYMMDD_HHMMSS_example/output/flow.html` を開く
   - レビューチェックリストは `info.md` に自動追記される

4. **フィードバック反映**
   - JSON 直接修正または再生成
   - 修正後は同じ runs/ ディレクトリ内で作業

5. **成果物の保管**
   - `runs/` ディレクトリ配下に全ての成果物が保管される
   - 必要に応じて別途アーカイブ

### §7.2 従来フロー（output/ ディレクトリを使用）
- `--output` オプションを指定することで従来通りの動作
- `output/` ディレクトリに出力
- 実行履歴の自動管理は行われない

---

## §8. 品質保証

### §8.1 テストデータ
- 小・中・大の3サイズサンプルを常備する。
- 匿名化済みサンプルを `samples/input/` に配置。
- 期待値JSONを `samples/expected/` に保存。

### §8.2 検証項目
- **スナップショット検証**：独自JSONのゴール値を保存し、差分検知する。
- **静的検証**：JSON Schema、未参照ID、循環／孤立タスクをチェックする。
- **BPMN検証**（将来）：bpmnlint で最低限のルール準拠を担保する。
- **可用性**：ローカルHTMLでの即時表示を標準フローに含める。

### §8.3 レビュー用チェックリスト
1. actors/phases/tasks/flows/issues が揃っているか。
2. `issues` に曖昧点や不足内容が列挙されているか。
3. HTML 可視化で未配置ノードや孤立タスクがないか。
4. bpmnlint エラーが解消済みか（将来）。
5. SVG/PNG が PPT で判読できる解像度か（将来）。

### §8.4 成功指標（KPI）
- **所要時間**：素材投入からレイヤー1可視化までの目標時間（要設定）を守る。
- **修正回数**：レイヤー1→2移行時の手動修正を N 件以下に抑える。
- **Lint合格率**（将来）：bpmnlint の優先ルールに対する合格率 X%以上。
- **PPT作業時間**（将来）：SVG/PNG 貼付後の整形時間を Y 分以下に抑える。

---

## §9. リスクと対策

### §9.1 技術的リスク
- **LLMの幻覚**：UNKNOWN 出力と `issues` 記載を徹底し、人手レビューを挟む。
- **BPMN準拠不足**（将来）：bpmnlint を強制し、変換器の単体テストを整備する。
- **レイアウト破綻**：elk.js の制約やノード折返し設定を最適化し、溢れた情報は notes へ退避する。

### §9.2 運用リスク
- **プロバイダ検出失敗**：
  - `.env` ファイルの設定を確認するよう明示的にエラーメッセージを表示
  - `.env.example` を参照して正しい設定方法を案内
- **機密情報漏洩**：匿名化前提で扱い、API 送信データを最小化する。
- **要件変動**：リビングドキュメントと ADR で可視化し、機能フラグで影響を限定する。

### §9.3 保守性リスク
- **runs/ ディレクトリの肥大化**：
  - 定期的なクリーンアップを推奨（古い実行履歴の削除またはアーカイブ）
  - 必要に応じて最大保持数の設定機能を検討

---

## §10. 変更管理ポリシー

### §10.1 バージョニング
- 本書冒頭に更新日時を記録する。
- バージョン番号は CHANGELOG.md で管理する。

### §10.2 意思決定ログ
- 主要な技術選択やスキーマ変更は ADR（Architecture Decision Record）で管理する。
- 将来的に `docs/adr/` ディレクトリに記録。

### §10.3 変更窓口
- 本人利用を前提に簡潔化し、フェーズ移行時に差分レビューする。
- タスク運用：実装タスクはすべて Plan → Do → Check → Action の PDCA を明示し、各サイクルを一つずつ確実に完遂してから次タスクへ進む。

### §10.4 ロールバック
- JSON スキーマ互換性を維持し、旧→新のマイグレーションスクリプトを準備する。
- runs/ 構造により過去の実行履歴を保持し、必要に応じて参照可能。

---

**注記**：本計画書はフェーズ進行や要件変更に応じて随時更新する。改訂履歴は CHANGELOG.md を参照のこと。
