# src ディレクトリについて

| サブディレクトリ | 役割 |
| --- | --- |
| `layer1/` | LLM 出力の整形・独自JSON生成ロジック。 |
| `layer2/` | JSON→BPMN 変換、bpmn-js 向けアセット生成。 |
| `export/` | SVG/PNG 生成やチェックリスト出力など最終成果物の輸出処理。 |

各サブディレクトリでは Python / TypeScript いずれにも対応できるよう、モジュール名は `flow_*` を基本とし、pytest でテスト可能な構成を保つ。
