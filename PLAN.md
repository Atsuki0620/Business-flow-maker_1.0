# Business-flow-maker 計画書

[最終更新日時] 2025年11月10日 22:24 JST

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
  - bpmn-js で `.bpmn` を表示し最終確認する。
  - bpmnlint でルールを検証し、SVG/PNG を出力して PPT へ貼り付ける。
  - **実装構造**: `src/core/bpmn_converter.py`（将来実装）

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

### §3.2 将来検討項目
- JSON→BPMN 変換（lanes, tasks, exclusiveGateway, sequenceFlow）
- bpmn-js 表示、bpmnlint チェック、SVG/PNG 出力
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

### §6.2 Layer2（BPMN パイプライン）実装状況

✅ **実装完了（v0.40）**:
- ✅ JSON→BPMN 2.0 XML 変換モジュール（`src/core/bpmn_converter.py`）
  - ✅ laneSet（泳線レーン）- 単一プロセス+レーン構造
  - ✅ task（タスクノード）- userTask/serviceTask対応
  - ✅ exclusiveGateway/parallelGateway/inclusiveGateway（ゲートウェイ）
  - ✅ sequenceFlow（フロー接続）- 条件式サポート
- ✅ 動的座標計算（`src/core/bpmn_layout.py`）- Sugiyamaアルゴリズム原理
- ✅ BPMN準拠性検証（`src/core/bpmn_validator.py`）
- ✅ 包括的テストスイート（`tests/test_bpmn_converter.py`）
- ✅ CLI実装（--input, --output, --validate, --debug）

🔄 **今後の拡張機能**:
- bpmn-js プレビュー機能（Web UI）
- SVG/PNG エクスポート機能
- bpmnlint 連携（BPMN仕様準拠チェック強化）
- レイアウトアルゴリズムの改善（完全なSugiyama実装、elk.js導入検討）
- 循環フロー検出

### §6.3 将来計画（v1.0.0 に向けて）
- ✅ Layer2（BPMN変換）の基本実装完了（v0.40）
- bpmn-js プレビュー機能の実装
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
