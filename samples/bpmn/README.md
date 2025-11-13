# BPMNサンプル出力

このディレクトリには、`samples/expected/`内のJSONフローサンプルから生成された代表的なBPMN 2.0 XMLファイルと対応するSVG可視化ファイルが含まれています。

## ファイル一覧

| サンプル | BPMN XML | SVG可視化 | 説明 |
|--------|----------|-----------|------|
| sample-tiny-01 | [sample-tiny-01.bpmn](./sample-tiny-01.bpmn) | [sample-tiny-01-bpmn.svg](./sample-tiny-01-bpmn.svg) | シンプルな調達フロー（2アクター、6タスク、1ゲートウェイ） |
| sample-small-01 | [sample-small-01.bpmn](./sample-small-01.bpmn) | [sample-small-01-bpmn.svg](./sample-small-01-bpmn.svg) | 小規模ビジネスプロセス（2アクター、4タスク） |
| sample-medium-01 | [sample-medium-01.bpmn](./sample-medium-01.bpmn) | [sample-medium-01-bpmn.svg](./sample-medium-01-bpmn.svg) | 従業員オンボーディングフロー（4アクター、4タスク、1ゲートウェイ） |
| sample-large-01 | [sample-large-01.bpmn](./sample-large-01.bpmn) | [sample-large-01-bpmn.svg](./sample-large-01-bpmn.svg) | 複雑な多部門プロセス |

## ファイルの閲覧方法

### BPMN XMLファイル（.bpmn）
`.bpmn`ファイルはBPMN 2.0準拠のXMLファイルで、以下のツールで開いて編集できます：
- [Camunda Modeler](https://camunda.com/download/modeler/)
- [bpmn.io](https://demo.bpmn.io/)
- その他のBPMN 2.0準拠ツール

### SVG可視化ファイル（.svg）
`.svg`ファイルは以下の方法で直接閲覧できます：
- Webブラウザ（ファイルをドラッグ&ドロップ）
- GitHub（ファイル表示時にブラウザで自動レンダリング）
- SVG対応の画像ビューアー
- Markdownドキュメントへの埋め込み

## 例：sample-tiny-01

これはシンプルな調達承認フローで、以下の要素を含みます：
- **2アクター（スイムレーン）**：営業部、総務部
- **6タスク**：必要性の確認、見積取得、依頼書作成、課長承認、総務承認、納品
- **1排他ゲートウェイ**：金額判定（¥100,000の閾値）
- **7シーケンスフロー**：条件分岐を含む

### プレビュー

![Sample Tiny 01 BPMN](./sample-tiny-01-bpmn.svg)

## BPMN 2.0の機能

生成されたすべてのBPMNファイルには以下が含まれます：
- ✅ **Collaboration構造**（参加者とレーン）
- ✅ **ユーザータスクとサービスタスク**（アクタータイプで区別）
- ✅ **ゲートウェイ**（排他、並行、包含）
- ✅ **シーケンスフロー**（条件式付き）
- ✅ **Diagram Interchange (DI)**（視覚表現）
- ✅ **動的レイアウト計算**（座標のハードコーディングなし）

## 生成コマンド

これらのファイルは以下のコマンドで生成されました：

```bash
python -m src.core.bpmn_converter \
  --input samples/expected/<sample-name>.json \
  --output samples/bpmn/<sample-name>.bpmn \
  --validate
```

コンバーターは`--no-svg`で無効化しない限り、BPMN XMLとSVG可視化の両方を自動生成します。

## バリデーション

このディレクトリ内のすべてのBPMNファイルは、組み込みバリデーターを使用してBPMN 2.0バリデーションに合格しています：

```bash
python -m src.core.bpmn_validator <file>.bpmn
```

## 関連情報

- [BPMN 2.0仕様](https://www.omg.org/spec/BPMN/2.0/)
- [BPMN視覚表現ガイド](https://www.bpmn.org/)
- [プロジェクトドキュメント](../../README.md)
