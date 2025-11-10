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

## ドキュメント更新ルール

### A. 日時フォーマット標準

各ドキュメントの最終更新日時は以下の形式で記載してください：

#### PLAN.md
```
[最終更新日時] YYYY年MM月DD日 HH:MM JST
```
- ファイル冒頭（タイトル直後）に記載
- 時刻は24時間表記
- タイムゾーンは必ずJSTを明記

#### CHANGELOG.md
```
[最終更新日時] YYYY年MM月DD日 HH:MM JST
```
- ファイル冒頭（タイトル直後）に記載
- バージョンエントリの形式：`### [vX.Y] - YYYY-MM-DD HH:MM JST`
- **重要**: 時刻を省略してはいけません

### B. ドキュメント更新チェックリスト

コミット前に以下を確認してください：

- [ ] PLAN.md を更新した場合、冒頭の `[最終更新日時]` を現在時刻に更新
- [ ] CHANGELOG.md に新しいバージョンを追加した場合、時刻を含む形式で記載
- [ ] すべてのバージョンエントリに時刻（HH:MM JST）が記載されている
- [ ] 日時フォーマットが統一されている（PLAN.md: `YYYY年MM月DD日 HH:MM JST`, CHANGELOG.md: `YYYY-MM-DD HH:MM JST`）

**確認用コマンド例**:
```bash
# PLAN.md の日時確認
grep -n "最終更新日時" PLAN.md

# CHANGELOG.md のバージョンエントリ確認
grep -n "^### \[v" CHANGELOG.md
```

### C. テンプレート

#### PLAN.md 冒頭の更新テンプレート
```markdown
# Business-flow-maker 計画書

[最終更新日時] 2025年11月10日 22:24 JST
```

#### CHANGELOG.md バージョンエントリのテンプレート
```markdown
### [v0.XX] - 2025-11-10 22:24 JST

#### 追加
- 新機能の説明

#### 変更
- 変更内容の説明

#### 修正
- バグ修正の説明

#### 削除
- 削除した機能の説明
```

**注意事項**:
- 時刻は実際の更新時刻を記載すること（例示の時刻をそのまま使わない）
- バージョンエントリは降順（新しいものが上）で記載
- 日時フォーマットを厳密に守ること
