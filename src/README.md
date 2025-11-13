# src ディレクトリ

Business-flow-makerの中核となるPythonモジュールを格納しています。業務フロー生成、BPMN変換、可視化の各機能を提供します。

## ディレクトリ構造

```
src/
├── core/               # 中核機能（JSON生成、BPMN変換）
│   ├── __init__.py
│   ├── generator.py          # JSON生成とスキーマ定義
│   ├── llm_client.py         # LLMクライアント（OpenAI/Azure OpenAI）
│   ├── bpmn_converter.py     # BPMN 2.0 XML変換
│   ├── bpmn_layout.py        # BPMN座標計算
│   ├── bpmn_validator.py     # BPMN検証
│   └── exceptions.py         # カスタム例外（v0.41追加予定）
├── visualizers/        # 可視化機能（HTML/SVG、Mermaid）
│   ├── __init__.py
│   ├── html_visualizer.py    # HTML+SVG泳線図生成
│   └── mermaid_visualizer.py # Mermaidフローチャート生成
└── utils/              # ユーティリティ
    ├── __init__.py
    └── run_manager.py        # runs/ディレクトリ管理
```

## サブディレクトリの役割

### core/（中核機能）

業務フロー生成とBPMN変換の中核ロジックを提供します。

#### generator.py
- **役割**: LLMを使った業務フローJSON生成
- **主要クラス**: `FlowDocument`（データクラス）
- **主要関数**:
  - `generate_flow()`: 入力文書からJSONを生成
  - `build_messages()`: Few-shot examples込みのLLMプロンプト構築
  - `normalize_flow_document()`: LLM出力の正規化・クリーニング
  - `validate()`: JSON Schema検証
- **CLI**: `python -m src.core.generator`

#### llm_client.py
- **役割**: LLMプロバイダの自動検出とクライアント生成
- **主要クラス**:
  - `LLMClient`（Protocol）: LLMクライアントのインターフェース
  - `OpenAILLMClient`: OpenAI API実装
  - `AzureOpenAILLMClient`: Azure OpenAI API実装
  - `ProviderDetector`: プロバイダ自動検出（v0.41リファクタリング予定）
- **主要関数**:
  - `detect_provider()`: Azure優先の自動検出
  - `create_llm_client()`: クライアントファクトリ
  - `cleanup_dummy_proxies()`: ダミープロキシ設定の無効化

#### bpmn_converter.py
- **役割**: JSON→BPMN 2.0 XML変換とSVG生成
- **主要クラス**:
  - `BPMNConverter`: BPMN XML生成
  - `BPMNSVGGenerator`: BPMN準拠SVG生成
- **主要関数**:
  - `convert_json_to_bpmn()`: メイン変換関数
- **CLI**: `python -m src.core.bpmn_converter`

#### bpmn_layout.py
- **役割**: BPMN要素の座標計算（Sugiyamaアルゴリズムベース）
- **主要クラス**:
  - `BPMNLayoutEngine`: レイアウトエンジン
- **主要関数**:
  - `calculate_positions()`: 全要素の座標計算
  - `_layer_assignment()`: レイヤー割り当て
  - `_calculate_horizontal_positions()`: 水平座標計算
  - `_calculate_vertical_positions()`: 垂直座標計算

#### bpmn_validator.py
- **役割**: BPMN 2.0準拠性の検証
- **主要関数**:
  - `validate_bpmn()`: BPMN XMLの妥当性検証

### visualizers/（可視化機能）

独自JSON形式のフローをHTML/SVG、Mermaid形式で可視化します。

#### html_visualizer.py
- **役割**: 泳線図（Swimlane）形式のHTML+SVG生成
- **主要関数**:
  - `build_layout()`: レイアウト計算
  - `build_svg()`: SVG生成
  - `build_html()`: HTML生成
- **CLI**: `python -m src.visualizers.html_visualizer`

#### mermaid_visualizer.py
- **役割**: Mermaid flowchart形式への変換
- **主要関数**:
  - `json_to_mermaid()`: JSON→Mermaid変換
- **CLI**: `python -m src.visualizers.mermaid_visualizer`

### utils/（ユーティリティ）

実行履歴管理などの補助機能を提供します。

#### run_manager.py
- **役割**: runs/ディレクトリでの実行履歴管理
- **主要関数**:
  - `create_run_dir()`: 実行ディレクトリの作成
  - `save_info_md()`: 実行情報の記録
  - `update_info_md()`: 実行情報の更新
  - `copy_input_file()`: 入力ファイルのバックアップ

## モジュール間の依存関係

```
┌─────────────────────────────────────┐
│ CLI (generator, bpmn_converter,     │
│      html_visualizer, etc.)         │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────┐      ┌────────────────────┐
│ core/generator.py    │──────│ core/llm_client.py │
└──────────┬───────────┘      └────────────────────┘
           │
           ├─────────────────────────────┐
           │                             │
           ▼                             ▼
┌─────────────────────┐      ┌──────────────────────┐
│ visualizers/        │      │ core/bpmn_converter  │
│ - html_visualizer   │      │ - bpmn_layout        │
│ - mermaid_visualizer│      │ - bpmn_validator     │
└─────────────────────┘      └──────────────────────┘
           │                             │
           └──────────┬──────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ utils/        │
              │ run_manager   │
              └───────────────┘
```

## テスト構成

各モジュールには対応するテストファイルが存在します：

- `tests/test_layer1_generator.py`: generator.pyのテスト
- `tests/test_bpmn_converter.py`: bpmn_converter.pyのテスト
- `tests/test_html_visualizer.py`: html_visualizer.pyのテスト（v0.41追加予定）
- `tests/test_mermaid_visualizer.py`: mermaid_visualizer.pyのテスト（v0.41追加予定）
- `tests/test_run_manager.py`: run_manager.pyのテスト（v0.41追加予定）

## 開発ガイドライン

### コーディング規約
- PEP 8準拠
- 命名規則: `snake_case`（関数、変数）、`PascalCase`（クラス）
- 型ヒント: Python 3.9+ `typing`モジュールを使用
- ドキュメント: Google Styleのdocstring

### 主要な設計パターン
- **Protocol**: LLMClientなどのインターフェース定義
- **Factory**: `create_llm_client()`などの生成関数
- **Data Class**: `FlowDocument`などのデータ構造

### 今後のリファクタリング予定（v0.41）
1. **カスタム例外の定義**: `core/exceptions.py`を追加し、`BPMNConversionError`, `LLMClientError`などを定義
2. **グローバル状態の解消**: `llm_client.py`の`_PROVIDER_CACHE`を`ProviderDetector`クラスに移動
3. **長大関数の分割**: `generator.py`の`normalize_flow_document()`を小関数に分割
4. **HTML テンプレートの外部化**: `html_visualizer.py`のHTMLテンプレートを外部ファイルに移動

詳細は[PLAN.md](../PLAN.md)および[AGENTS.md](../AGENTS.md)を参照してください。
