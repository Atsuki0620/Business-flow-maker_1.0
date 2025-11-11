"""
LLM Client Builder for Business-flow-maker.

This module provides:
- LLM provider auto-detection (Azure OpenAI / OpenAI)
- Client factory and Protocol definition
- Environment validation utilities
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv() -> None:  # type: ignore
        return None

load_dotenv()

try:
    from openai import AzureOpenAI, OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    AzureOpenAI = None  # type: ignore
    OpenAI = None  # type: ignore


class LLMClient(Protocol):
    """Interface for LLM backends."""

    def structured_flow(self, *, messages: List[Dict[str, str]], schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Return a JSON document that satisfies the given schema."""


def cleanup_dummy_proxies() -> None:
    """HTTP(S)_PROXY がダミー値なら環境変数から除去する。"""

    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        value = os.getenv(key)
        if value and is_dummy_value(value):
            os.environ.pop(key, None)
            logger.warning(f"{key} はダミー値のため無効化しました。")


def is_dummy_value(value: str) -> bool:
    """ダミー値判定（XXX, your-, 10文字未満など）"""

    if not value:
        return True

    stripped = value.strip()
    if len(stripped) < 10:
        return True

    lower = stripped.lower()
    dummy_tokens = ("xxx", "your-")
    return any(token in lower for token in dummy_tokens)


def validate_openai_env() -> bool:
    """OPENAI_API_KEYが有効か"""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.info("OpenAI: OPENAI_API_KEY が未設定です。")
        return False
    if is_dummy_value(api_key):
        logger.warning("OpenAI: OPENAI_API_KEY がダミー値のため利用できません。")
        return False
    return True


def validate_azure_env() -> bool:
    """Azure必須3変数が有効か"""

    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "").strip()
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()

    missing = []
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")
    if not api_version:
        missing.append("AZURE_OPENAI_API_VERSION")
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")

    if missing:
        logger.info(f"AzureOpenAI: {', '.join(missing)} が未設定です。")
        return False

    if any(is_dummy_value(value) for value in (api_key, api_version, endpoint)):
        logger.warning("AzureOpenAI: 必須環境変数にダミー値が含まれています。")
        return False

    return True


_PROVIDER_CACHE: Optional[str] = None
_PROVIDER_ERRORS: List[str] = []


def detect_provider() -> Optional[str]:
    """
    "azure" | "openai" | None を返す（環境変数チェックのみ）
    Azure優先、標準出力にログ出力
    SDK初期化は create_llm_client() 内で実施
    """

    global _PROVIDER_CACHE, _PROVIDER_ERRORS

    if _PROVIDER_CACHE is not None:
        return _PROVIDER_CACHE

    errors: List[str] = []
    cleanup_dummy_proxies()

    # Azure環境変数のチェック
    if validate_azure_env():
        logger.info("Azure OpenAI を使用します。")
        _PROVIDER_CACHE = "azure"
        _PROVIDER_ERRORS = []
        return _PROVIDER_CACHE
    else:
        errors.append("AzureOpenAI: 必須環境変数(AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_ENDPOINT)を正しく設定してください。")

    # OpenAI環境変数のチェック
    if validate_openai_env():
        logger.info("OpenAI API を使用します。")
        _PROVIDER_CACHE = "openai"
        _PROVIDER_ERRORS = []
        return _PROVIDER_CACHE
    else:
        errors.append("OpenAI: OPENAI_API_KEY が未設定かダミー値です。")

    _PROVIDER_CACHE = None
    _PROVIDER_ERRORS = errors

    logger.error("有効な LLM プロバイダを検出できませんでした。")
    for message in errors:
        logger.error(f" - {message}")

    return None


def _extract_json_payload(text: str) -> str:
    """Markdownコードブロックを除去してJSONペイロードを抽出する。"""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped[3:]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        end_idx = stripped.rfind("```")
        if end_idx != -1:
            stripped = stripped[:end_idx]
    return stripped.strip()


class OpenAILLMClient:
    """OpenAI Chat Completions API wrapper that requests JSON-schema constrained output."""

    def __init__(self) -> None:
        if OpenAI is None:
            raise ImportError("openai SDK is not installed. Run `pip install openai`.")
        self._client = OpenAI()

    def structured_flow(self, *, messages: List[Dict[str, str]], schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        """LLM APIを呼び出してJSON形式のフローを生成する。

        Args:
            messages: チャットメッセージリスト（system, user, assistantロール）
            schema: JSON Schema（辞書形式）
            model: モデル名

        Returns:
            パース済みのJSON辞書

        Raises:
            RuntimeError: API呼び出しまたはJSONパースに失敗した場合
            ValueError: レスポンスが空の場合
        """
        logger.debug(f"LLMリクエスト: model={model}, messages={str(messages)[:500]}...")

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"name": "FlowSchema", "schema": schema}},
            )
        except Exception as exc:
            logger.error(f"OpenAI API呼び出しに失敗しました: {exc}")
            raise RuntimeError(f"OpenAI API呼び出しに失敗しました: {exc}") from exc

        # レスポンスの取得
        if not response.choices or not response.choices[0].message.content:
            logger.error("LLMからのレスポンスが空です。")
            raise ValueError("LLMからのレスポンスが空です。")

        content = response.choices[0].message.content
        logger.debug(f"LLMレスポンス: {content[:500]}...")
        payload = _extract_json_payload(content)

        try:
            result = json.loads(payload)
            logger.debug(f"JSONパース成功: {len(payload)} bytes")
            return result
        except json.JSONDecodeError as exc:
            logger.error(f"JSONのパースに失敗しました。レスポンス内容: {payload[:200]}...")
            raise RuntimeError(f"JSONのパースに失敗しました。レスポンス内容: {payload[:200]}...") from exc


class AzureOpenAILLMClient:
    """AzureOpenAI Chat Completions API用クライアント（LLMClient Protocolに準拠）"""

    def __init__(self) -> None:
        if AzureOpenAI is None:
            raise ImportError("openai SDK がインストールされていません。`pip install openai` を実行してください。")

        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]

        self._client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

    def structured_flow(self, *, messages: List[Dict[str, str]], schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        """LLM APIを呼び出してJSON形式のフローを生成する。

        Args:
            messages: チャットメッセージリスト（system, user, assistantロール）
            schema: JSON Schema（辞書形式）
            model: モデル名

        Returns:
            パース済みのJSON辞書

        Raises:
            RuntimeError: API呼び出しまたはJSONパースに失敗した場合
            ValueError: レスポンスが空の場合
        """
        logger.debug(f"LLMリクエスト: model={model}, messages={str(messages)[:500]}...")

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"name": "FlowSchema", "schema": schema}},
            )
        except Exception as exc:
            logger.error(f"Azure OpenAI API呼び出しに失敗しました: {exc}")
            raise RuntimeError(f"Azure OpenAI API呼び出しに失敗しました: {exc}") from exc

        # レスポンスの取得
        if not response.choices or not response.choices[0].message.content:
            logger.error("LLMからのレスポンスが空です。")
            raise ValueError("LLMからのレスポンスが空です。")

        content = response.choices[0].message.content
        logger.debug(f"LLMレスポンス: {content[:500]}...")
        payload = _extract_json_payload(content)

        try:
            result = json.loads(payload)
            logger.debug(f"JSONパース成功: {len(payload)} bytes")
            return result
        except json.JSONDecodeError as exc:
            logger.error(f"JSONのパースに失敗しました。レスポンス内容: {payload[:200]}...")
            raise RuntimeError(f"JSONのパースに失敗しました。レスポンス内容: {payload[:200]}...") from exc


def create_llm_client() -> LLMClient:
    """detect_provider()の結果に基づきクライアント生成"""

    provider = detect_provider()
    if provider == "azure":
        return AzureOpenAILLMClient()
    if provider == "openai":
        return OpenAILLMClient()

    hint = "\n".join(f"- {message}" for message in _PROVIDER_ERRORS) or "- LLM プロバイダ用の環境変数が不足しています。"
    raise RuntimeError(f"LLM プロバイダを自動検出できませんでした。\n{hint}")
