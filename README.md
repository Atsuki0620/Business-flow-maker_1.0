# Business-flow-maker

## プロジェクト概要

**Business-flow-maker** は、業務フローの下書きをLLMで構造化し、視覚化・BPMN変換まで自動化するツールです。

### 主な機能

- マニュアルや業務文書から業務フローの独自JSON（actors/phases/tasks/flows/issues）を生成
- HTML+SVG による泳線図（Swimlane）の可視化
- Mermaid フローチャート形式への変換
- BPMN 2.0 XML への変換（将来実装）
- JSON Schema による厳格な検証とレビューチェックリスト自動生成

### 対象ユーザー

- 業務マニュアルを整備する担当者
- システム要件定義でフローを可視化したいエンジニア
- 小規模から部署横断まで対応できる柔軟性を求める方

---

## インストール手順

### 前提条件

- **Python 3.9 以上**（推奨: 3.11 以上）
- **pip** と **venv** モジュール
- **LLM API キー**（OpenAI または Azure OpenAI）

### 手順

1. **リポジトリをクローン**

```bash
git clone <repository-url>
cd Business-flow-maker_1.0
```

2. **仮想環境を作成・有効化**

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **依存パッケージをインストール**

```bash
pip install -r requirements.txt
```

4. **環境変数を設定**

`.env.example` をコピーして `.env` を作成し、API キーを設定します。

```bash
# Windows
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` ファイルを編集して、API キーを設定：

**プロバイダは自動検出されます**（Azure OpenAI 優先）。いずれかの環境変数を設定してください。

```env
# Azure OpenAI を使用する場合（推奨）
AZURE_OPENAI_API_KEY=***
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# OpenAI を使用する場合
OPENAI_API_KEY=sk-***
```

---

## クイックスタート

### 1. JSON 生成（Layer1）

業務フローの文書から独自JSONを生成します。

```bash
# runs/構造を使用（推奨）：実行履歴を自動管理
python -m src.core.generator \
  --input samples/input/sample-small-01.md \
  --stub samples/expected/sample-small-01.json

# 従来の出力先を指定（後方互換性）
python -m src.core.generator \
  --input samples/input/sample-small-01.md \
  --stub samples/expected/sample-small-01.json \
  --output output/flow.json

# LLM実行モード（API使用）
python -m src.core.generator \
  --input samples/input/sample-medium-01.md \
  --model gpt-4o-mini

# DEBUGログを有効化（LLMリクエスト・レスポンス全文を表示）
python -m src.core.generator \
  --input samples/input/sample-medium-01.md \
  --model gpt-4o-mini \
  --debug
```

**runs/構造について**:
- `--output` を省略すると、`runs/YYYYMMDD_HHMMSS_{input_stem}/` に実行履歴が自動保存されます
- 各実行ディレクトリには以下が含まれます：
  - `info.md`: 実行情報（実行コマンド、入力ファイル情報、JSON検証結果、レビューチェックリスト）
  - `output/`: 生成されたファイル（flow.json、flow.html、flow.svg など）
  - 入力ファイルのコピー（再現性確保）

### 2. HTML可視化

生成したJSONを泳線図として可視化します。

```bash
# runs/構造のJSONを指定（info.mdに自動記録）
python -m src.visualizers.html_visualizer \
  --json runs/20251110_123456_sample-small-01/output/flow.json \
  --html runs/20251110_123456_sample-small-01/output/flow.html \
  --svg runs/20251110_123456_sample-small-01/output/flow.svg

# 従来の出力先を指定
python -m src.visualizers.html_visualizer \
  --json output/flow.json \
  --html output/flow.html \
  --svg output/flow.svg
```

ブラウザで生成された `.html` ファイルを開いて確認できます。

### 3. Mermaid フローチャート生成

```bash
# runs/構造のJSONを指定（info.mdに自動記録）
python -m src.visualizers.mermaid_visualizer \
  --json runs/20251110_123456_sample-small-01/output/flow.json \
  --output runs/20251110_123456_sample-small-01/output/flow.mmd

# 従来の出力先を指定
python -m src.visualizers.mermaid_visualizer \
  --json output/flow.json \
  --output output/flow.mmd
```

生成された `flow.mmd` は Mermaid 対応エディタやブラウザ拡張で表示できます。

---

## プロジェクト構成

```
Business-flow-maker_1.0/
├── src/
│   ├── core/              # JSON生成、BPMN変換の中核機能
│   │   ├── generator.py
│   │   ├── llm_client.py
│   │   └── bpmn_converter.py
│   ├── visualizers/       # HTML/SVG、Mermaid生成
│   │   ├── html_visualizer.py
│   │   └── mermaid_visualizer.py
│   └── utils/             # 実行履歴管理など
│       └── run_manager.py
├── schemas/               # JSON Schema定義
├── samples/               # 入力・出力サンプル
├── runs/                  # 実行履歴の自動管理（初回実行時に自動生成）
├── tests/                 # pytestによる自動テスト
├── PLAN.md                # 開発計画書（詳細設計）
├── CHANGELOG.md           # 変更履歴
├── AGENTS.md              # 開発ガイドライン
└── README.md              # 本ファイル
```

---

## 詳細ドキュメント

- **[CONCEPTS.md](docs/CONCEPTS.md)**: データモデル概念定義（タスク/ゲートウェイの使い分け、BPMN 2.0準拠ガイド）
- **[PLAN.md](PLAN.md)**: 開発計画書（アーキテクチャ、スコープ、実装ステップ）
- **[CHANGELOG.md](CHANGELOG.md)**: 改訂履歴とバージョン管理
- **[AGENTS.md](AGENTS.md)**: 開発者向けガイドライン（コーディング規約、テスト指針）

---

## テスト実行

```bash
# 全テスト実行
pytest

# 特定のテストのみ
pytest tests/test_layer1_generator.py

# カバレッジ付き
pytest --cov=src
```

---

## ライセンス

（ライセンス情報を追加予定）

---

## 貢献・フィードバック

本プロジェクトは個人利用を主目的としています。フィードバックや改善提案は Issue でお知らせください。
