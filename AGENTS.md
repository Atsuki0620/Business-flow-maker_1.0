# Repository Guidelines

## はじめに
本リポジトリは業務フローをLLMで整形し、HTML・BPMN・画像まで落とし込む計画をまとめています。常に最新の `PLAN.md` を参照し、ドキュメント化されていない判断は必ず追記してください。日本語で簡潔かつ丁寧に回答してくださいい。

## プロジェクト構成と配置
- `PLAN.md`: 開発計画の単一ソース。更新ごとに版情報を先頭へ追記。
- `src/`: JSON生成・整形・BPMN変換などのPython/TypeScriptスクリプトを配置予定。機能別に `layer1/`, `layer2/`, `export/` サブフォルダを切る。
- `schemas/`: 独自JSONおよびBPMNテンプレートのSchemaとサンプル。
- `samples/`: 匿名化済みの入力素材と期待されるJSON/BPMN出力。
- `output/`: 最新の `flow.json`, `flow.bpmn`, `flow.svg`, `flow.png` をフェーズ別に保管。

## ビルド・テスト・開発コマンド
- `python -m venv .venv && .\\.venv\\Scripts\\activate`: 仮想環境を作成し依存を分離。
- `pip install -r requirements.txt`: LLM補助スクリプトや可視化ツールの依存を導入。
- `pytest`: 変換器と検証ロジックの単体テストを実行。必ず成功させてからコミット。
- `npm install && npm run visualize`: bpmn-js/elk.js ベースのフロント資産をビルドしローカルで静的確認。
- `npm run lint` または `bpmnlint output/flow.bpmn`: BPMNルール逸脱を検出。

## コーディング規約と命名
PythonはPEP8・4スペースインデント、TypeScript/JSはESLint標準＋Prettier 2スペースを採用。モジュール名は `flow_*`, 関数は `verb_object`、クラスはPascalCase。JSONキーはスネークケースを固定し、欠落情報は `issues[].note` に明示します。

## テスト指針
pytestで各レイヤーのユニットテストを配置し、サンプル3サイズ（小・中・大）をフィクスチャ化。BPMN出力は `bpmnlint` とHTMLプレビューのスクリーンショットを残し、重大欠陥はIssue化。回帰防止のため、再現素材と期待出力を `samples/expected/` に保存します。

## コミットとプルリク
コミットは `type: subject`（例: `feat: add flow generator`）で統一し、粒度はフェーズ境界を越えないこと。PRでは目的・主要変更点・確認手順・スクリーンショットを簡潔に列挙し、関連Issueとテスト結果を添付。バイナリや生成物を含める場合は理由と再生成手順を必ず記述してください。レビュー前に `git status` がクリーンであること、必要ならバックアップブランチを残すことも忘れずに。
