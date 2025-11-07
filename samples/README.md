# samples ディレクトリ

- `input/`：匿名化済みの入力素材（小・中・大の3サイズを想定）。
- `expected/`：レイヤー別に期待される JSON / BPMN / 画像などの出力サンプル。

各サンプルは `sample-{size}-{id}.md`（入力説明）と `sample-{size}-{id}.json`（出力）を揃え、pytest フィクスチャから参照できる形で管理する。
