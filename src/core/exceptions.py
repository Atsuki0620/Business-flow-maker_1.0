"""
Business-flow-maker用のカスタム例外クラス。

このモジュールでは、アプリケーション固有のエラーを明示的に表現するための
カスタム例外クラスを定義しています。
"""

from __future__ import annotations


class BusinessFlowMakerError(Exception):
    """Business-flow-makerの基底例外クラス。"""
    pass


class LLMClientError(BusinessFlowMakerError):
    """LLMクライアント関連のエラー。"""
    pass


class ProviderDetectionError(LLMClientError):
    """LLMプロバイダの検出に失敗した場合のエラー。"""
    pass


class LLMAPIError(LLMClientError):
    """LLM APIの呼び出しに失敗した場合のエラー。"""
    pass


class JSONParseError(LLMClientError):
    """LLMレスポンスのJSONパースに失敗した場合のエラー。"""
    pass


class BPMNConversionError(BusinessFlowMakerError):
    """BPMN変換関連のエラー。"""
    pass


class BPMNLayoutError(BPMNConversionError):
    """BPMNレイアウト計算に失敗した場合のエラー。"""
    pass


class BPMNValidationError(BPMNConversionError):
    """BPMN検証に失敗した場合のエラー。"""
    pass


class SchemaValidationError(BusinessFlowMakerError):
    """JSON Schema検証に失敗した場合のエラー。"""
    pass


class VisualizationError(BusinessFlowMakerError):
    """可視化（HTML/SVG/Mermaid）関連のエラー。"""
    pass


class HTMLGenerationError(VisualizationError):
    """HTML生成に失敗した場合のエラー。"""
    pass


class SVGGenerationError(VisualizationError):
    """SVG生成に失敗した場合のエラー。"""
    pass


class MermaidGenerationError(VisualizationError):
    """Mermaid生成に失敗した場合のエラー。"""
    pass


class FileIOError(BusinessFlowMakerError):
    """ファイル入出力関連のエラー。"""
    pass


class RunManagerError(BusinessFlowMakerError):
    """runs/ディレクトリ管理関連のエラー。"""
    pass
