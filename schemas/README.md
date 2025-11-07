# schemas ディレクトリ

- `flow.schema.json`：独自JSON（actors/phases/tasks/flows/issues など）の最新スキーマ。
- `bpmn-template.xml`：BPMN 2.0 テンプレートやプレースホルダを置く予定。
- `samples/`：将来的にスキーマ例やバリデーション用スニペットを追加。

スキーマは PEP8/ESLint に沿った命名 (`snake_case`) を維持し、欠落情報は JSON 内の `issues[].note` に明示する。
