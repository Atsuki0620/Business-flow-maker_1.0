# Business-flow-maker 計画書

[最終更新] 2025年11月10日 00:00 JST

## 参照ドキュメント
- [README.md](README.md) - プロジェクト概要とクイックスタート
- [CHANGELOG.md](CHANGELOG.md) - 改訂履歴とバージョン管理
- [AGENTS.md](AGENTS.md) - 開発者向けガイドライン

---

## 0. 背景・目的・前提
- **目的**：マニュアル整備やシステム要件整理に使える業務フローを、短時間で下書きから確定形まで落とし込める仕組みを整備する。
- **入力**：文章、業務文書、箇条書き、Excel など（構造化／非構造データ混在、複数ファイル結合可）。
- **出力**：
  - 中間生成物：独自JSON（actors/phases/tasks/flows/issues 等）とブラウザで確認できる静的HTML。
  - 確定成果物：BPMN 2.0 XML（.bpmn）と bpmn-js プレビュー、SVG/PNG 画像。PPTX は当面手動貼り付け。
  - Excel：Actors/Tasks/Flows/RACI/Issues を表形式で出力。
- **利用想定**：個人利用が主。小規模〜部署横断まで対応できる柔軟性を確保。
- **技術方針**：LLM は OpenAI API / Azure OpenAI API を利用。API キーやエンドポイント、利用プロバイダ種別（例：`LLM_PROVIDER=openai|azure`）は `.env`（git 未管理）に格納し、実装からは環境変数経由で参照する。起動時にユーザーへプロバイダ選択を促し、選択結果に応じて OpenAI/Azure それぞれのクライアント設定を切り替える。CLI/スクリプト中心で、必要に応じて Streamlit 等を検討。
- **正規化フロー**：正規化＆クリーニング工程は MVP では省略。要望が高まった段階でオプション機能として追加。

---

## 1. 成果イメージと二層構成
- **レイヤー1（LLM 親和な下書き）**
  - LLM で独自JSON（actors/phases/tasks/flows/issues）を生成する。
  - HTML+JS（elk.js 等）で自動レイアウトしたSVGを表示する。
  - JSON Schema 検証と軽量な体裁チェック、レビュー用チェックリストを自動出力する。
  - **実装構造**: `src/core/generator.py` + `src/visualizers/`（HTML/SVG、Mermaid生成）
- **レイヤー2（BPMN 準拠の確定形）**
  - 独自JSONを BPMN 2.0 XML へ変換する。
  - bpmn-js で `.bpmn` を表示し最終確認する。
  - bpmnlint でルールを検証し、SVG/PNG を出力して PPT へ貼り付ける。
  - **実装構造**: `src/core/bpmn_converter.py`

---

## 2. スコープ（MVP と強化項目）
### 2.1 MVP に含める
- 文章／複数ファイルの取り込みと軽微な整形。
- LLM による独自JSON生成と厳格スキーマ（未知は UNKNOWN）出力。
- JSON Schema 検証と構造・必須項目の欠落チェック。
- HTML（ローカル静的サイト）による可視化と自動レイアウト。
- JSON→BPMN 変換（lanes, tasks, exclusiveGateway, sequenceFlow）。
- bpmn-js 表示、bpmnlint チェック、SVG/PNG 出力。
- レビュー用チェックリストの自動生成。
### 2.2 後続で検討する項目
- 入力の高度な正規化／クリーニング、表記ゆれ辞書、ID 採番強化。
- UI フレームワーク固定（Streamlit 等）やコラボ機能。
- PPTX 自動生成（python-pptx 等）。
- RAG による過去フロー・規程集・社内用語辞書の参照。

---

## 3. 要件
### 3.1 機能要件
1. **独自JSON生成**：actors, phases, tasks（責任/RACI/handoff_to/systems/notes を含む）、gateways、flows、issues を出力し、曖昧な点は `issues` に列挙する。
2. **ブラウザ可視化（レイヤー1）**：JSON を読み込み、泳走レーン／縦積みレイアウトで SVG 化し、未参照IDや孤立ノードも検知する。
   - Windowsローカル確認を優先し、HTML/SVG/レビューはUTF-8(BOM付)で書き出す。Swimlane内タスク/ゲートウェイはレーン中央に整列させ図の崩れを抑制（2025-11-08 Hotfix）。
3. **BPMN変換（レイヤー2）**：laneSet、task、exclusiveGateway、sequenceFlow を生成し、bpmn-js＋bpmnlint で検証する。
4. **エクスポート**：SVG/PNG を高解像度で出力し、PPT 貼付に耐える品質を確保する。
5. **レビュー出力**：本書 §8 のチェックリストと Lint 結果をテキストで出力する。
### 3.2 非機能要件
- **再現性**：同じ入力で同等の JSON 構造を返す（温度／プロンプト管理）。
- **可搬性**：ローカル実行／オフライン可視化を前提とする。
- **拡張性**：正規化・PPT 自動化・UI 導入を後付けできるアーキテクチャ。
- **セキュリティ**：機微情報はローカル保持。API 送信前に匿名化オプションを用意。

---

## 4. 実装ステップ（イラスト）
**Phase 0：キックオフ**
- 匿名化済み入力サンプル3件を準備。
- JSON スキーマ草案（actors/phases/tasks/flows/issues）を確定。
**Phase 1：レイヤー1のMVP**
- LLM 呼び出しで JSON を生成（関数呼び出し／テンプレート）。
- JSON Schema 検証とエラーレポートを整備。
- HTML+JS で SVG 可視化、elk.js で自動配置。
- レビュー用チェックリスト出力を自動化。
**Phase 2：レイヤー2のMVP**
- JSON→BPMN 2.0 変換器を実装。
- bpmn-js 表示と bpmnlint ルール検証を行う。
- SVG/PNG 書き出しと PPT 貼付動線を整備。
**Phase 3：改良サイクル**
- レイアウト調整（レーン再配置／ラベル折返し）。
- Lint ルールのチューニング（未接続フロー、重複タスク名など）。
- 運用チェックリストと出力確認プロセスを整備。
### 4.x .env 運用ポリシー
- .env は実行直前に対象プロバイダのテンプレート（例: .env.openai / .env.azure）をコピーして生成し、作業後は削除する。設定を混在させない。
- OpenAI API 利用時は LLM_PROVIDER=openai と OPENAI_API_KEY のみを記述し、HTTP_PROXY / HTTPS_PROXY は空のままにする。切替コマンド例: Copy-Item .env.openai .env。
- Azure OpenAI 利用時は LLM_PROVIDER=azure / API_KEY / API_VERSION / AZURE_ENDPOINT に加え、必要に応じて HTTP_PROXY / HTTPS_PROXY を .env.azure に記述し、Copy-Item .env.azure .env で展開する。
- .env は Git 管理外だが、どの設定で成果物を生成したかを PLAN 改訂履歴・PR 説明・output/README.md に記録してトレーサビリティを確保する。
- .env.example を最新テンプレートとして維持し、OpenAI/Azure それぞれの必須変数と注意事項をコメントで明記する。

**Phase 4：任意拡張**
- 正規化＆クリーニング機能、表記ゆれ辞書、ID 採番の強化。
- PPTX 自動化とテンプレレイアウト。
- UI 導入（ブラウザ or デスクトップ）と RAG 連携の検討。
### 4.1 開発環境セットアップ（2025-11-08 更新）
- **仮想環境**：python -m venv .venv で環境を作成し、Windows では .\.venv\Scripts\activate で有効化する。再利用時も同じシェルでコマンドを実行する。
- **依存導入**：pip install -r requirements.txt を実行すると openai>=1.44.0・jsonschema>=4.22.0・python-dotenv>=1.0.1 が揃い、Layer1 スクリプト／テストの前提が整う。
- **環境変数**：.env に LLM_PROVIDER=openai|azure、OPENAI_API_KEY=sk-***（Azure 利用時は AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com と AZURE_OPENAI_API_KEY= も追記）を保存する。python-dotenv が src/layer1/generator.py 読み込み時に自動でロードし、OpenAI/Azure SDK が参照する。
- **実行コマンド**：
  - スタブ検証：python -m src.core.generator --input samples/input/sample-small-01.md --stub samples/expected/sample-small-01.json --output output/flow.json
  - 本番 API：python -m src.core.generator --input <input.md> --model gpt-4.1-mini（Azure モデル利用時は .env の LLM_PROVIDER とエンドポイントで切り替える）
- **確認ポイント**：output/flow.json が更新され JSON Schema 検証が成功すること、API キー未設定時は SDK がエラーを返し問題箇所を特定できることをログへ残す。


---

## 5. 変更管理とリビングドキュメント運用
- **バージョニング**：本書冒頭に版番号・日付・変更要約を追記する。
- **意思決定ログ**：主要な技術選択やスキーマ変更は ADR で管理する。
- **変更窓口**：本人利用を前提に簡潔化し、フェーズ移行時に差分レビューする。
- **ロールバック**：JSON スキーマ互換性を維持し、旧→新のマイグレーションスクリプトを準備する。
- **タスク運用**：実装タスクはすべて Plan → Do → Check → Action の PDCA を明示し、各サイクルを一つずつ確実に完遂してから次タスクへ進む。

---

## 6. 品質保証とQA
- **テストデータ**：小・中・大の3サイズサンプルを常備する。
- **スナップショット**：独自JSONのゴール値を保存し、差分検知する。
- **静的検証**：JSON Schema、未参照ID、循環／孤立タスクをチェックする。
- **BPMN検証**：bpmnlint で最低限のルール準拠を担保する。
- **可用性**：ローカルHTMLでの即時表示を標準フローに含める。

---

## 7. 成功指標（KPI/評価）
- **所要時間**：素材投入からレイヤー1可視化までの目標時間（要設定）を守る。
- **修正回数**：レイヤー1→2移行時の手動修正を N 件以下に抑える。
- **Lint合格率**：bpmnlint の優先ルールに対する合格率 X%以上。
- **PPT作業時間**：SVG/PNG 貼付後の整形時間を Y 分以下に抑える。

---

## 8. レビュー用チェックリスト（雛形）
1. actors/phases/tasks/flows/issues が揃っているか。
2. `issues` に曖昧点や不足内容が列挙されているか。
3. HTML 可視化で未配置ノードや孤立タスクがないか。
4. bpmnlint エラーが解消済みか。
5. SVG/PNG が PPT で判読できる解像度か。

---

## 9. リスクと対策
- **LLMの幻覚**：UNKNOWN 出力と `issues` 記載を徹底し、人手レビューを挟む。
- **BPMN準拠不足**：bpmnlint を強制し、変換器の単体テストを整備する。
- **レイアウト破綻**：elk.js の制約やノード折返し設定を最適化し、溢れた情報は notes へ退避する。
- **機密情報**：匿名化前提で扱い、API 送信データを最小化する。
- **要件変動**：リビングドキュメントと ADR で可視化し、機能フラグで影響を限定する。

---

## 10. 運用フロー（標準作業）
1. 素材収集と匿名化。
2. LLM で独自JSONを生成（レイヤー1）。
3. HTML 表示で目視＋チェックリスト評価。
4. フィードバック反映（JSON 直接修正 or 再生成）。
5. JSON→BPMN 変換（レイヤー2）。
6. bpmn-js で目視確認＋bpmnlint 検証。
7. SVG/PNG をエクスポートし、PPT へ貼付。
8. JSON/BPMN/画像を `output/` に保管し、ADR を更新。

---

## 11. 成果物・保管方針
- 独自JSON：`output/flow.json`（最新版を常に更新）。
- HTML可視化ファイル：ローカルで開ける静的一式。
- BPMNファイル：`output/flow.bpmn`。
- 画像：`output/flow.svg` / `output/flow.png`。
- レビュー記録：チェックリスト結果、Lintログ、ADR。

---

## 12. 次の一歩と実行トリガー
- Phase0/1 を開始し、サンプル3件で **レイヤー1のMVP** を完成させる。
  - JSON スキーマ妥当性
  - 可視化の視認性
  - チェックリストの有効性
- 合格後に Phase2（レイヤー2）へ進む。

**注記**：本計画書はフェーズ進行や要件変更に応じて随時更新し、版情報を冒頭に追記する。

---
