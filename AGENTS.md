# Repository Guidelines

## はじめに
本リポジトリは業務フローをLLMで整形し、HTML・BPMN・画像まで落とし込む計画をまとめています。常に最新のドキュメントを参照し、ドキュメント化されていない判断は必ず追記してください。日本語で簡潔かつ丁寧に回答してください。

## 必読ドキュメント
開発時は以下の順番でドキュメントを参照してください：

1. **[README.md](README.md)** - プロジェクト概要とクイックスタート（最初に読む）
2. **[PLAN.md](PLAN.md)** - 開発計画の詳細（アーキテクチャ、スコープ、実装ステップ）
3. **[CHANGELOG.md](CHANGELOG.md)** - 改訂履歴とバージョン管理

## プロジェクト構成と配置
- `README.md`: プロジェクト概要、インストール、クイックスタート。
- `PLAN.md`: 開発計画の単一ソース。詳細設計とアーキテクチャ。
- `CHANGELOG.md`: 全ての重要な変更履歴を時系列で記録。
- `src/core/`: JSON生成（generator.py）、LLMクライアント（llm_client.py）、BPMN変換（bpmn_converter.py）。
- `src/visualizers/`: HTML/SVG可視化（html_visualizer.py）、Mermaid生成（mermaid_visualizer.py）。
- `src/utils/`: 実行管理（run_manager.py）など補助機能。
- `runs/`: 実行履歴の自動管理ディレクトリ（タイムスタンプ付き）。
- `schemas/`: JSON Schema定義とBPMNテンプレート。
- `samples/`: 匿名化済みの入力素材と期待されるJSON/BPMN出力。

## ビルド・テスト・開発コマンド
- `python -m venv .venv && .\\.venv\\Scripts\\activate`: 仮想環境を作成し依存を分離。
- `pip install -r requirements.txt`: LLM補助スクリプトや可視化ツールの依存を導入。
- `pytest`: 変換器と検証ロジックの単体テストを実行。必ず成功させてからコミット。
- `npm install && npm run visualize`: bpmn-js/elk.js ベースのフロント資産をビルドしローカルで静的確認。
- `npm run lint` または `bpmnlint output/flow.bpmn`: BPMNルール逸脱を検出。

## コーディング規約と命名
PythonはPEP8・4スペースインデント、TypeScript/JSはESLint標準＋Prettier 2スペースを採用。モジュール名は `flow_*`, 関数は `verb_object`、クラスはPascalCase。JSONキーはスネークケースを固定し、欠落情報は `issues[].note` に明示します。関数やクラスのdocstringはすべて日本語で記載し、入力・出力・例外などの補足情報も日本語で整理してください。

## テスト指針
pytestで各レイヤーのユニットテストを配置し、サンプル3サイズ（小・中・大）をフィクスチャ化。BPMN出力は `bpmnlint` とHTMLプレビューのスクリーンショットを残し、重大欠陥はIssue化。回帰防止のため、再現素材と期待出力を `samples/expected/` に保存します。

## コミットとプルリク
コミットは `type: subject`（例: `feat: add flow generator`）で統一し、粒度はフェーズ境界を越えないこと。PRでは目的・主要変更点・確認手順・スクリーンショットを簡潔に列挙し、関連Issueとテスト結果を添付。バイナリや生成物を含める場合は理由と再生成手順を必ず記述してください。レビュー前に `git status` がクリーンであること、必要ならバックアップブランチを残すことも忘れずに。
