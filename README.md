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

`.env` ファイルを編集して、LLM プロバイダと API キーを設定：

```env
# OpenAI を使用する場合
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-***

# Azure OpenAI を使用する場合
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=***
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

---

## クイックスタート

### 1. JSON 生成（Layer1）

業務フローの文書から独自JSONを生成します。

```bash
# スタブモード（API不要、サンプルJSONで検証）
python -m src.layer1.flow_json_generator \
  --input samples/input/sample-small-01.md \
  --stub samples/expected/sample-small-01.json \
  --output output/flow.json

# LLM実行モード（API使用）
python -m src.layer1.flow_json_generator \
  --input samples/input/sample-medium-01.md \
  --model gpt-4o-mini \
  --output output/flow.json
```

### 2. HTML可視化

生成したJSONを泳線図として可視化します。

```bash
python -m src.export.visualizer \
  --json output/flow.json \
  --html output/flow.html \
  --svg output/flow.svg
```

ブラウザで `output/flow.html` を開いて確認できます。

### 3. Mermaid フローチャート生成

```bash
python -m src.export.mermaid_generator \
  --json output/flow.json \
  --output output/flow.mmd
```

生成された `flow.mmd` は Mermaid 対応エディタやブラウザ拡張で表示できます。

---

## プロジェクト構成（移行中）

現在、ディレクトリ構造を以下の形に移行中です：

```
Business-flow-maker_1.0/
├── src/
│   ├── core/              # 将来: JSON生成、BPMN変換の中核機能
│   │   ├── generator.py
│   │   ├── llm_client.py
│   │   └── bpmn_converter.py
│   ├── visualizers/       # 将来: HTML/SVG、Mermaid生成
│   │   ├── html_visualizer.py
│   │   └── mermaid_visualizer.py
│   ├── utils/             # 将来: 実行履歴管理など
│   │   └── run_manager.py
│   ├── layer1/            # 現在: JSON生成
│   ├── layer2/            # 現在: BPMN変換（未実装）
│   └── export/            # 現在: 可視化
├── schemas/               # JSON Schema定義
├── samples/               # 入力・出力サンプル
├── output/                # 生成物の保存先（将来 runs/ に移行）
├── runs/                  # 将来: 実行履歴の自動管理
├── tests/                 # pytestによる自動テスト
├── PLAN.md                # 開発計画書（詳細設計）
├── CHANGELOG.md           # 変更履歴
├── AGENTS.md              # 開発ガイドライン
└── README.md              # 本ファイル
```

---

## 詳細ドキュメント

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
