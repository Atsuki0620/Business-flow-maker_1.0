# output ディレクトリ

常に最新の成果物を配置する。フェーズごとにサブフォルダを切る場合は `phase-<n>/flow.*` の形で管理する。

| ファイル | 内容 |
| --- | --- |
| `flow.json` | レイヤー1の確定版独自JSON。 |
| `flow.bpmn` | レイヤー2の BPMN 2.0 XML。 |
| `flow.svg` / `flow.png` | bpmn-js から書き出した画像。 |

lint ログやレビュー記録を追加する場合は `logs/` サブディレクトリを作成する。
