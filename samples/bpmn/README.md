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

各サンプルの完全な生成手順を以下に示します。

### sample-tiny-01の生成手順

```bash
# 1. コマンド実行
python -m src.core.bpmn_converter \
  --input samples/expected/sample-tiny-01.json \
  --output samples/bpmn/sample-tiny-01.bpmn \
  --svg-output samples/bpmn/sample-tiny-01-bpmn.svg \
  --validate

# 2. 生成されるファイル
# - samples/bpmn/sample-tiny-01.bpmn: BPMN 2.0 XML
# - samples/bpmn/sample-tiny-01-bpmn.svg: SVG画像

# 3. ツールでの確認方法
# - Camunda Modelerで sample-tiny-01.bpmn を開く
# - ブラウザで sample-tiny-01-bpmn.svg を開く
# - GitHub上で直接SVGをプレビュー
```

### 他のサンプルも同様に生成可能

```bash
# sample-small-01
python -m src.core.bpmn_converter \
  --input samples/expected/sample-small-01.json \
  --output samples/bpmn/sample-small-01.bpmn \
  --svg-output samples/bpmn/sample-small-01-bpmn.svg \
  --validate

# sample-medium-01
python -m src.core.bpmn_converter \
  --input samples/expected/sample-medium-01.json \
  --output samples/bpmn/sample-medium-01.bpmn \
  --svg-output samples/bpmn/sample-medium-01-bpmn.svg \
  --validate

# sample-large-01
python -m src.core.bpmn_converter \
  --input samples/expected/sample-large-01.json \
  --output samples/bpmn/sample-large-01.bpmn \
  --svg-output samples/bpmn/sample-large-01-bpmn.svg \
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

### 推奨ツール

#### Camunda Modeler（デスクトップ）
- **URL**: https://camunda.com/download/modeler/
- **特徴**: オープンソース、無料、編集・検証機能が充実
- **対応OS**: Windows、macOS、Linux
- **用途**: BPMN図の編集、検証、プロセス設計

#### bpmn.io（Webベース）
- **URL**: https://demo.bpmn.io/
- **特徴**: ブラウザ上で動作、インストール不要
- **用途**: クイックプレビュー、共有リンク生成

### その他の対応ツール

#### Visual Paradigm
- **URL**: https://www.visual-paradigm.com/
- **特徴**: UMLなど他の図も統合管理可能
- **用途**: エンタープライズ向けモデリング

#### Signavio Process Manager
- **URL**: https://www.signavio.com/
- **特徴**: クラウドベース、コラボレーション機能
- **用途**: チーム間での業務プロセス管理

#### Bizagi Modeler
- **URL**: https://www.bizagi.com/
- **特徴**: 無料、ドキュメント生成機能付き
- **用途**: プロセスドキュメンテーション、シミュレーション

#### Enterprise Architect
- **URL**: https://www.sparxsystems.com/
- **特徴**: エンタープライズアーキテクチャ全般に対応
- **用途**: 大規模システム設計、要件管理

### 互換性について

- すべてのサンプルBPMNファイルは **OMG BPMN 2.0 Specification** に準拠しています
- 上記のツールで問題なく開けることを確認しています
- カスタム属性や拡張要素は使用していないため、高い互換性が保証されます

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
