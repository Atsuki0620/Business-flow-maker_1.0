# samples ディレクトリ

業務フロー生成のサンプル入力・出力を格納しています。各サンプルは複雑度に応じて4段階のサイズに分類されています。

## ディレクトリ構造

```
samples/
├── input/          # 入力文書（Markdown形式）
├── expected/       # 期待されるJSON出力
└── bpmn/           # BPMN 2.0 XML/SVG出力サンプル（v0.40追加）
```

## サンプルサイズと特徴

### tiny（極小）
- **特徴**: 最小構成のフロー（1-2アクター、3-5タスク）
- **用途**: 基本機能の確認、単体テスト
- **ファイル例**:
  - `input/sample-tiny-01.md`: 簡単な承認フロー
  - `expected/sample-tiny-01.json`: 対応するJSON出力
  - `bpmn/sample-tiny-01.bpmn`: BPMN 2.0 XML
  - `bpmn/sample-tiny-01-bpmn.svg`: BPMN SVG画像

### small（小）
- **特徴**: 中規模のフロー（2-3アクター、5-10タスク、ゲートウェイ1-2個）
- **用途**: Few-shot examples、統合テスト
- **ファイル例**:
  - `input/sample-small-01.md`: 部署間連携フロー
  - `expected/sample-small-01.json`: 対応するJSON出力
  - `bpmn/sample-small-01.bpmn`: BPMN 2.0 XML
  - `bpmn/sample-small-01-bpmn.svg`: BPMN SVG画像

### medium（中）
- **特徴**: 実用的なフロー（3-5アクター、10-20タスク、ゲートウェイ3-5個）
- **用途**: 実業務レビュー、パフォーマンステスト
- **ファイル例**:
  - `input/sample-medium-01.md`: 複雑な業務プロセス
  - `expected/sample-medium-01.json`: 対応するJSON出力
  - `bpmn/sample-medium-01.bpmn`: BPMN 2.0 XML
  - `bpmn/sample-medium-01-bpmn.svg`: BPMN SVG画像

### large（大）
- **特徴**: 大規模フロー（5+アクター、20+タスク、複雑なゲートウェイ構造）
- **用途**: スケーラビリティテスト、限界値確認
- **ファイル例**:
  - `input/sample-large-01.md`: 部署横断の複雑なワークフロー
  - `expected/sample-large-01.json`: 対応するJSON出力
  - `bpmn/sample-large-01.bpmn`: BPMN 2.0 XML
  - `bpmn/sample-large-01-bpmn.svg`: BPMN SVG画像

## 命名規則

- **入力文書**: `sample-{size}-{id}.md`
- **JSON出力**: `sample-{size}-{id}.json`
- **BPMN XML**: `sample-{size}-{id}.bpmn`
- **BPMN SVG**: `sample-{size}-{id}-bpmn.svg`

例: `sample-small-01.md` → `sample-small-01.json` → `sample-small-01.bpmn`

## 使用方法

### サンプルを使ったJSON生成テスト

```bash
# stubモードでサンプルJSONを読み込み
python -m src.core.generator \
  --input samples/input/sample-small-01.md \
  --stub samples/expected/sample-small-01.json

# LLMを使った実際の生成
python -m src.core.generator \
  --input samples/input/sample-small-01.md \
  --model gpt-4o-mini
```

### サンプルを使ったBPMN変換テスト

```bash
# サンプルJSONからBPMN生成
python -m src.core.bpmn_converter \
  --input samples/expected/sample-small-01.json \
  --output output/flow.bpmn \
  --svg-output output/flow-bpmn.svg \
  --validate
```

## pytest での利用

テストフィクスチャから参照できる形で管理されています。

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_tiny_input():
    return Path("samples/input/sample-tiny-01.md")

@pytest.fixture
def sample_tiny_expected():
    return Path("samples/expected/sample-tiny-01.json")
```
