# Business-flow-maker

## プロジェクト概要

**Business-flow-maker** は、業務フローの下書きをLLMで構造化し、視覚化・BPMN変換まで自動化するツールです。

### 主な機能

- マニュアルや業務文書から業務フローの独自JSON（actors/phases/tasks/flows/issues）を生成
- HTML+SVG による泳線図（Swimlane）の可視化
- Mermaid フローチャート形式への変換
- **BPMN 2.0 XML への変換とSVG可視化（v0.40で実装完了）**
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

### 4. BPMN 2.0 XML変換とSVG可視化

業務フローをBPMN 2.0準拠のXMLとSVG画像に変換します。

```bash
# runs/構造のJSONを指定（info.mdに自動記録）
python -m src.core.bpmn_converter \
  --input runs/20251110_123456_sample-small-01/output/flow.json \
  --validate

# 手動で出力先を指定
python -m src.core.bpmn_converter \
  --input samples/expected/sample-tiny-01.json \
  --output output/flow.bpmn \
  --svg-output output/flow-bpmn.svg \
  --validate

# デバッグモードで詳細情報を表示
python -m src.core.bpmn_converter \
  --input samples/expected/sample-tiny-01.json \
  --validate \
  --debug
```

**主な機能**:
- JSON → BPMN 2.0 XML 変換（OMG BPMN 2.0 Specification完全準拠）
- SVG画像の自動生成（GitHub上で直接プレビュー可能）
- スイムレーン構造の実装（actors → participant/lane要素）
- ゲートウェイのサポート（exclusive/parallel/inclusive）
- 動的座標計算（Sugiyamaアルゴリズムベース）
- BPMN 2.0準拠性の自動検証

**生成されるファイル**:
- `flow.bpmn`: BPMN 2.0 XML（Camunda Modeler等で開けます）
- `flow-bpmn.svg`: BPMN準拠のSVG画像（ブラウザで表示可能）

**サンプル出力**: [samples/bpmn/](samples/bpmn/) ディレクトリにサンプル出力があります。

### 5. 完全なワークフロー例（入力文書→BPMN出力まで）

業務マニュアルから BPMN 2.0 準拠の成果物を生成する完全な手順：

```bash
# ステップ1: 入力文書からJSONを生成
python -m src.core.generator \
  --input samples/input/sample-medium-01.md \
  --model gpt-4o-mini

# 出力例: runs/20251113_140530_sample-medium-01/output/flow.json

# ステップ2: HTML可視化でレビュー
python -m src.visualizers.html_visualizer \
  --json runs/20251113_140530_sample-medium-01/output/flow.json \
  --html runs/20251113_140530_sample-medium-01/output/flow.html \
  --svg runs/20251113_140530_sample-medium-01/output/flow.svg

# ブラウザでflow.htmlを開いてフローを確認

# ステップ3: BPMN 2.0 XML/SVGを生成
python -m src.core.bpmn_converter \
  --input runs/20251113_140530_sample-medium-01/output/flow.json \
  --validate

# 出力ファイル（runs/ディレクトリ内に自動生成）:
# - flow.bpmn: Camunda Modelerで編集可能なBPMN 2.0 XML
# - flow-bpmn.svg: GitHub上でプレビュー可能なSVG画像

# ステップ4: 実行情報を確認
cat runs/20251113_140530_sample-medium-01/info.md
```

**生成物の活用方法**:
- `flow.html`: ブラウザで開き、業務フローのレビューに使用
- `flow.bpmn`: Camunda Modeler、bpmn.io等のBPMNエディタで編集・共有
- `flow-bpmn.svg`: ドキュメントやプレゼンテーションに貼り付け
- `info.md`: 生成履歴の記録、再現性確保

---

## プロジェクト構成

```
Business-flow-maker_1.0/
├── src/
│   ├── core/              # JSON生成、BPMN変換の中核機能
│   │   ├── generator.py
│   │   ├── llm_client.py
│   │   ├── bpmn_converter.py
│   │   ├── bpmn_layout.py
│   │   └── bpmn_validator.py
│   ├── visualizers/       # HTML/SVG、Mermaid生成
│   │   ├── html_visualizer.py
│   │   └── mermaid_visualizer.py
│   └── utils/             # 実行履歴管理など
│       └── run_manager.py
├── schemas/               # JSON Schema定義
├── samples/               # 入力・出力サンプル
│   ├── input/             # 入力文書サンプル
│   ├── expected/          # 期待されるJSON出力
│   └── bpmn/              # BPMN出力サンプル（v0.40追加）
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

## ユースケース例

### 業務マニュアル作成
- **課題**: 口頭で伝わっている業務手順を文書化したい
- **活用方法**:
  1. 業務担当者にヒアリングした内容をMarkdownで記述
  2. LLMでJSON化し、HTMLで可視化してレビュー
  3. フィードバックを反映後、BPMN出力して正式マニュアルに添付

### システム要件定義
- **課題**: 開発チームに業務フローを正確に伝えたい
- **活用方法**:
  1. 業務部門の要望文書からJSON生成
  2. BPMN 2.0 XMLを出力し、Camunda Modelerで編集
  3. システム要件定義書にSVGを貼り付け、開発チームと共有

### 業務プロセス改善
- **課題**: 現行業務の問題点を可視化したい
- **活用方法**:
  1. 現行フローをJSON化し、`issues`フィールドに改善点を記録
  2. HTML可視化で問題箇所を赤色表示
  3. 改善後フローと比較して効果を検証

### 部署間連携フローの整理
- **課題**: 複数部署にまたがる業務の責任分界点が不明確
- **活用方法**:
  1. actorsに各部署を定義し、tasksにhandoff_toを明記
  2. 泳線図（Swimlane）で部署間の受け渡しを可視化
  3. RACI情報を追加して責任範囲を明確化

---

## トラブルシューティング

### API接続エラー

**症状**: `LLMプロバイダを検出できませんでした`というエラーが表示される

**対処法**:
1. `.env`ファイルが存在し、正しく設定されているか確認
   ```bash
   cat .env
   ```
2. 環境変数が正しくロードされているか確認
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
   ```
3. APIキーがダミー値（`xxx`, `your-`など）でないか確認
4. Azure OpenAIの場合、3つの環境変数すべてが設定されているか確認
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_VERSION`

### プロバイダ検出失敗

**症状**: 環境変数を設定したのにOpenAIが検出されない

**対処法**:
1. ダミープロキシ設定が残っていないか確認
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```
2. プロキシ環境変数がダミー値の場合は削除
   ```bash
   unset HTTP_PROXY
   unset HTTPS_PROXY
   ```
3. `--debug`フラグで詳細ログを確認
   ```bash
   python -m src.core.generator --input samples/input/sample-tiny-01.md --model gpt-4o-mini --debug
   ```

### BPMN検証エラー

**症状**: `BPMN 2.0準拠性の検証に失敗しました`というエラーが表示される

**対処法**:
1. 入力JSONのflows配列を確認（fromとtoが正しく設定されているか）
2. gatewaysに2つ以上の出力フローがあるか確認
3. `--debug`フラグで詳細なエラー情報を確認
   ```bash
   python -m src.core.bpmn_converter --input output/flow.json --validate --debug
   ```
4. 検証をスキップしてBPMNを生成する場合（非推奨）
   ```bash
   python -m src.core.bpmn_converter --input output/flow.json
   ```

### JSON Schema検証エラー

**症状**: `JSON Schema検証に失敗しました`というエラーが表示される

**対処法**:
1. 生成されたJSONファイルの構造を確認
   ```bash
   cat output/flow.json | python -m json.tool
   ```
2. 必須フィールドが存在するか確認（actors, phases, tasks, flows, issues）
3. `--skip-validation`フラグで検証をスキップ（デバッグ用）
   ```bash
   python -m src.core.generator --input samples/input/sample-small-01.md --skip-validation
   ```

### runs/ディレクトリが作成されない

**症状**: `--output`を省略しても`runs/`ディレクトリが作成されない

**対処法**:
1. 書き込み権限があるか確認
   ```bash
   ls -la | grep runs
   ```
2. 手動でディレクトリを作成
   ```bash
   mkdir runs
   ```
3. `--output`を明示的に指定
   ```bash
   python -m src.core.generator --input samples/input/sample-small-01.md --output output/flow.json
   ```

### 文字化け（Windows）

**症状**: HTMLやSVGファイルをブラウザで開くと日本語が文字化けする

**対処法**:
1. ファイルがUTF-8（BOM付き）で保存されているか確認
2. ブラウザの文字エンコーディング設定をUTF-8に変更
3. エディタで再保存する際にUTF-8を指定

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
