# BPMN 2.0サンプル出力

このディレクトリには、Business-flow-makerで生成されたBPMN 2.0準拠のXMLファイルとSVG可視化ファイルが格納されています。

## ファイル一覧

### sample-tiny-01（備品購入申請フロー）
- **BPMN XML**: `sample-tiny-01.bpmn`
- **SVG画像**: `sample-tiny-01-bpmn.svg`
- **元データ**: `samples/expected/sample-tiny-01.json`

最小規模のサンプル。2つのactor、3つのphase、6つのtask、1つのgatewayを含みます。

### sample-small-01
- **BPMN XML**: `sample-small-01.bpmn`
- **SVG画像**: `sample-small-01-bpmn.svg`
- **元データ**: `samples/expected/sample-small-01.json`

小規模のサンプル。複数の部署間でのワークフローを表現します。

### sample-medium-01
- **BPMN XML**: `sample-medium-01.bpmn`
- **SVG画像**: `sample-medium-01-bpmn.svg`
- **元データ**: `samples/expected/sample-medium-01.json`

中規模のサンプル。より複雑な分岐とタスクの連携を含みます。

### sample-large-01
- **BPMN XML**: `sample-large-01.bpmn`
- **SVG画像**: `sample-large-01-bpmn.svg`
- **元データ**: `samples/expected/sample-large-01.json`

大規模のサンプル。実際の業務プロセスに近い複雑なフローを表現します。

## 生成方法

これらのファイルは以下のコマンドで生成されました：

```bash
python -m src.core.bpmn_converter \
  --input samples/expected/sample-tiny-01.json \
  --output samples/bpmn/sample-tiny-01.bpmn \
  --svg-output samples/bpmn/sample-tiny-01-bpmn.svg \
  --validate
```

## GitHubでのプレビュー

SVGファイルはGitHubのWebインターフェースで直接プレビュー可能です。各ファイルをクリックすると、ブラウザ上でBPMN図を確認できます。

例：
- [sample-tiny-01-bpmn.svg](./sample-tiny-01-bpmn.svg)
- [sample-small-01-bpmn.svg](./sample-small-01-bpmn.svg)
- [sample-medium-01-bpmn.svg](./sample-medium-01-bpmn.svg)
- [sample-large-01-bpmn.svg](./sample-large-01-bpmn.svg)

## BPMN XMLの用途

生成されたBPMN XMLファイルは、以下のツールで開くことができます：

- **Camunda Modeler**: オープンソースのBPMNモデラー
- **bpmn.io**: Webベースのビューワー
- **その他のBPMN 2.0対応ツール**

## 技術仕様

- **BPMN バージョン**: 2.0
- **準拠規格**: OMG BPMN 2.0 Specification
- **エンコーディング**: UTF-8
- **座標計算**: Sugiyamaアルゴリズムベースの動的レイアウト

## 更新情報

- **v0.40** (2025-11-13): BPMN 2.0変換機能の初回リリース
  - JSON→BPMN XML変換
  - SVG可視化機能
  - BPMN 2.0準拠性検証
