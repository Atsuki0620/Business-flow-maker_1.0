"""
Flow JSON generator for Layer1 (LLM-friendly draft).

This module provides:
- dataclass representations for the schema
- a pluggable LLM client interface (OpenAI Responses API or dummy/mocked client)
- JSON Schema validation helper
- CLI entry point for local runs
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Protocol

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

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    jsonschema = None  # type: ignore


@dataclass
class FlowDocument:
    actors: List[Dict[str, Any]]
    phases: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    flows: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    gateways: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # Remove None entries for optional fields
        return {k: v for k, v in payload.items() if v is not None}


class LLMClient(Protocol):
    """Interface for LLM backends."""

    def structured_flow(self, *, prompt: str, schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Return a JSON document that satisfies the given schema."""


class OpenAILLMClient:
    """OpenAI Responses API wrapper that requests JSON-schema constrained output."""

    def __init__(self) -> None:
        if OpenAI is None:
            raise ImportError("openai SDK is not installed. Run `pip install openai`.")
        self._client = OpenAI()

    def structured_flow(self, *, prompt: str, schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        request_kwargs = {
            "model": model,
            "input": prompt,
        }
        try:
            response = self._client.responses.create(
                response_format={"type": "json_schema", "json_schema": {"name": "FlowSchema", "schema": schema}},
                **request_kwargs,
            )
        except TypeError:
            # Older openai SDKs (< 1.43) do not support response_format.
            response = self._client.responses.create(**request_kwargs)
        content = response.output[0].content[0].text if response.output else "{}"
        payload = _extract_json_payload(content)
        return json.loads(payload)


class DummyLLMClient:
    """Simple client that loads a pre-built JSON file for offline testing."""

    def __init__(self, stub_path: pathlib.Path) -> None:
        self._stub_path = stub_path

    def structured_flow(self, *, prompt: str, schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        _ = prompt, schema, model
        return json.loads(self._stub_path.read_text(encoding="utf-8"))


def cleanup_dummy_proxies() -> None:
    """HTTP(S)_PROXY がダミー値なら環境変数から除去する。"""

    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        value = os.getenv(key)
        if value and is_dummy_value(value):
            os.environ.pop(key, None)
            print(f"[layer1] {key} はダミー値のため無効化しました。")


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
        print("[layer1] OpenAI: OPENAI_API_KEY が未設定です。")
        return False
    if is_dummy_value(api_key):
        print("[layer1] OpenAI: OPENAI_API_KEY がダミー値のため利用できません。")
        return False
    return True


def validate_azure_env() -> bool:
    """Azure必須3変数が有効か"""

    api_key = os.getenv("API_KEY", "").strip()
    api_version = os.getenv("API_VERSION", "").strip()
    endpoint = os.getenv("AZURE_ENDPOINT", "").strip()

    missing = []
    if not api_key:
        missing.append("API_KEY")
    if not api_version:
        missing.append("API_VERSION")
    if not endpoint:
        missing.append("AZURE_ENDPOINT")

    if missing:
        print(f"[layer1] AzureOpenAI: {', '.join(missing)} が未設定です。")
        return False

    if any(is_dummy_value(value) for value in (api_key, api_version, endpoint)):
        print("[layer1] AzureOpenAI: 必須環境変数にダミー値が含まれています。")
        return False

    return True


def test_openai_available() -> bool:
    """OpenAI SDKの初期化テスト（軽量、API呼び出しなし）"""

    if OpenAI is None:
        print("[layer1] OpenAI SDK がインストールされていません。`pip install openai` を実行してください。")
        return False

    try:
        OpenAI()
    except Exception as exc:  # pragma: no cover - SDK内部の例外をそのまま通知
        print(f"[layer1] OpenAI クライアント初期化に失敗しました: {exc}")
        return False
    return True


def test_azure_available() -> bool:
    """AzureOpenAI SDKの初期化テスト（軽量、API呼び出しなし）"""

    if AzureOpenAI is None:
        print("[layer1] AzureOpenAI 用の openai SDK がインストールされていません。`pip install openai` を実行してください。")
        return False

    try:
        AzureOpenAI(
            api_key=os.environ["API_KEY"],
            api_version=os.environ["API_VERSION"],
            azure_endpoint=os.environ["AZURE_ENDPOINT"],
        )
    except Exception as exc:  # pragma: no cover - SDK内部の例外をそのまま通知
        print(f"[layer1] AzureOpenAI クライアント初期化に失敗しました: {exc}")
        return False
    return True


_PROVIDER_CACHE: Optional[str] = None
_PROVIDER_ERRORS: List[str] = []


def detect_provider() -> Optional[str]:
    """
    "azure" | "openai" | None を返す
    Azure優先、標準出力にログ出力
    """

    global _PROVIDER_CACHE, _PROVIDER_ERRORS

    if _PROVIDER_CACHE is not None:
        return _PROVIDER_CACHE

    errors: List[str] = []
    cleanup_dummy_proxies()

    if validate_azure_env():
        if test_azure_available():
            print("[layer1] Azure OpenAI を使用します。")
            _PROVIDER_CACHE = "azure"
            _PROVIDER_ERRORS = []
            return _PROVIDER_CACHE
        errors.append("AzureOpenAI: SDK 初期化に失敗しました。")
    else:
        errors.append("AzureOpenAI: 必須環境変数(API_KEY, API_VERSION, AZURE_ENDPOINT)を正しく設定してください。")

    if validate_openai_env():
        if test_openai_available():
            print("[layer1] OpenAI API を使用します。")
            _PROVIDER_CACHE = "openai"
            _PROVIDER_ERRORS = []
            return _PROVIDER_CACHE
        errors.append("OpenAI: SDK 初期化に失敗しました。")
    else:
        errors.append("OpenAI: OPENAI_API_KEY が未設定かダミー値です。")

    _PROVIDER_CACHE = None
    _PROVIDER_ERRORS = errors

    print("[layer1] 有効な LLM プロバイダを検出できませんでした。")
    for message in errors:
        print(f" - {message}")

    return None


class AzureOpenAILLMClient:
    """AzureOpenAI用クライアント（LLMClient Protocolに準拠）"""

    def __init__(self) -> None:
        if AzureOpenAI is None:
            raise ImportError("openai SDK がインストールされていません。`pip install openai` を実行してください。")

        api_key = os.environ["API_KEY"]
        api_version = os.environ["API_VERSION"]
        endpoint = os.environ["AZURE_ENDPOINT"]

        self._client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

    def structured_flow(self, *, prompt: str, schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        request_kwargs = {
            "model": model,
            "input": prompt,
        }
        response = self._client.responses.create(
            response_format={"type": "json_schema", "json_schema": {"name": "FlowSchema", "schema": schema}},
            **request_kwargs,
        )
        content = response.output[0].content[0].text if response.output else "{}"
        payload = _extract_json_payload(content)
        return json.loads(payload)


def create_llm_client() -> LLMClient:
    """detect_provider()の結果に基づきクライアント生成"""

    provider = detect_provider()
    if provider == "azure":
        return AzureOpenAILLMClient()
    if provider == "openai":
        return OpenAILLMClient()

    hint = "\n".join(f"- {message}" for message in _PROVIDER_ERRORS) or "- LLM プロバイダ用の環境変数が不足しています。"
    raise RuntimeError(f"LLM プロバイダを自動検出できませんでした。\n{hint}")


def load_schema(schema_path: pathlib.Path) -> Dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def build_prompt(input_text: str) -> str:
    base = (
        "���Ȃ��͋Ɩ��t���[�A�[�L�e�N�g�ł��B�ȉ��̓��͂�ǂ݁A"
        "actors / phases / tasks / flows / gateways / issues / metadata ���܂� JSON �𐶐����Ă��������B\n"
        f"--- INPUT START ---\n{input_text}\n--- INPUT END ---\n\n"
        "�K�{���[��:\n"
        "1. JSON Schema �ɏ������Asnake_case �L�[���ێ�����B\n"
        "2. �B���܂��͕s���ȏ��� issues[].note �ɋL�^���AUNKNOWN �Ƃ�������܂߂�B\n"
        "3. flows[].condition �͕K�v�ȏꍇ�̂݋L�ڂ���B\n"
        "4. tasks[].handoff_to �͋�z��ł��K���܂߂�B\n"
    )
    extras = (
        "5. actors[].id �ƃ^�X�N[].actor_id �͑S�ẴA�N�^�[ID���g�p����B\n"
        "6. metadata �́Aid/title/source/last_updated�݂̂𗘗p����B\n"
        "7. ���͂� ``` �������Ȃ��ł���������JSON���Ԃ��B\n"
    )
    return base + extras




def _extract_json_payload(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped[3:]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        end_idx = stripped.rfind("```")
        if end_idx != -1:
            stripped = stripped[:end_idx]
    return stripped.strip()


def _slugify_id(value: str, prefix: str, idx: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not base:
        base = f"{prefix}_{idx}"
    if not base.startswith(prefix):
        base = f"{prefix}_{base}"
    return base


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if item]


def _pick_identifier(value):
    if value is None:
        return None
    if isinstance(value, list):
        for item in value:
            if item:
                return str(item)
        return None
    return str(value)


def normalize_flow_document(raw: dict) -> dict:
    data = dict(raw)

    actors = []
    actor_lookup = {}
    for idx, actor in enumerate(data.get("actors", []), start=1):
        name = actor.get("name") or actor.get("title") or actor.get("role") or f"actor_{idx}"
        actor_id = actor.get("id") or _slugify_id(name, "actor", idx)
        actor_type = actor.get("type") or ("system" if "system" in (actor.get("role", "").lower()) else "human")
        filtered = {"id": actor_id, "name": name, "type": actor_type}
        if "notes" in actor:
            filtered["notes"] = actor["notes"]
        actors.append(filtered)
        actor_lookup[name] = actor_id
        actor_lookup[actor_id] = actor_id
    if not actors:
        actors = [{"id": "actor_1", "name": "unspecified", "type": "human"}]
        actor_lookup["unspecified"] = "actor_1"
    data["actors"] = actors

    phases = []
    phase_lookup = {}
    for idx, phase in enumerate(data.get("phases", []), start=1):
        name = phase.get("name") or phase.get("title") or f"phase_{idx}"
        phase_id = phase.get("id") or _slugify_id(name, "phase", idx)
        filtered = {"id": phase_id, "name": name}
        if "description" in phase:
            filtered["description"] = phase["description"]
        phases.append(filtered)
        phase_lookup[name] = phase_id
        phase_lookup[phase_id] = phase_id
    if not phases:
        phases = [{"id": "phase_1", "name": "unknown"}]
        phase_lookup["unknown"] = "phase_1"
    data["phases"] = phases

    tasks = []
    for idx, task in enumerate(data.get("tasks", []), start=1):
        name = task.get("name") or task.get("title") or f"task_{idx}"
        task_id = task.get("id") or _slugify_id(name, "task", idx)
        phase_key = _pick_identifier(task.get("phase_id") or task.get("phase"))
        phase_id = phase_lookup.get(phase_key)
        if not phase_id:
            phase_id = phases[0]["id"]
        actor_key = _pick_identifier(task.get("actor_id") or task.get("actor"))
        actor_id = actor_lookup.get(actor_key)
        if not actor_id:
            actor_id = actors[0]["id"]
        entry = {
            "id": task_id,
            "name": name,
            "actor_id": actor_id,
            "phase_id": phase_id,
        }
        entry["handoff_to"] = _as_list(task.get("handoff_to"))
        systems = _as_list(task.get("systems"))
        if systems:
            entry["systems"] = systems
        if "notes" in task:
            entry["notes"] = task["notes"]
        tasks.append(entry)
    if not tasks:
        tasks = [{"id": "task_1", "name": "unknown", "actor_id": actors[0]["id"], "phase_id": phases[0]["id"], "handoff_to": []}]
    data["tasks"] = tasks

    flows = []
    for idx, flow in enumerate(data.get("flows", []), start=1):
        flow_id = flow.get("id") or f"flow_{idx}"
        entry = {
            "id": flow_id,
            "from": flow.get("from") or flow.get("source") or "",
            "to": flow.get("to") or flow.get("target") or "",
        }
        if flow.get("condition"):
            entry["condition"] = flow["condition"]
        if flow.get("notes"):
            entry["notes"] = flow["notes"]
        flows.append(entry)
    flows = [f for f in flows if f["from"] and f["to"]]
    if not flows:
        flows = [{"id": "flow_1", "from": tasks[0]["id"], "to": tasks[-1]["id"]}]
    data["flows"] = flows

    gateways = []
    for idx, gateway in enumerate(data.get("gateways", []), start=1):
        name = gateway.get("name") or gateway.get("title") or f"gateway_{idx}"
        gateway_id = gateway.get("id") or _slugify_id(name, "gateway", idx)
        entry = {"id": gateway_id, "name": name, "type": gateway.get("type", "exclusive")}
        if "notes" in gateway:
            entry["notes"] = gateway["notes"]
        gateways.append(entry)
    data["gateways"] = gateways

    issues = []
    severity_choices = {"info", "warning", "critical"}
    for idx, issue in enumerate(data.get("issues", []), start=1):
        issue_id = issue.get("id") or f"issue_{idx}"
        note = issue.get("note") or issue.get("description") or "UNKNOWN"
        entry = {"id": issue_id, "note": note}
        severity = issue.get("severity")
        if severity:
            sev = severity.lower()
            if sev in severity_choices:
                entry["severity"] = sev
        issues.append(entry)
    data["issues"] = issues

    metadata = data.get("metadata", {})
    today = date.today().isoformat()
    data["metadata"] = {
        "id": metadata.get("id", "sample-flow"),
        "title": metadata.get("title", metadata.get("name", "LLM generated flow")),
        "source": metadata.get("source", "samples/input/sample-small-01.md"),
        "last_updated": metadata.get("last_updated", today),
    }

    return data




def validate(document: Dict[str, Any], schema: Dict[str, Any]) -> None:
    if jsonschema is None:
        raise RuntimeError("jsonschema が未インストールのため検証できません。`pip install jsonschema` を実行してください。")
    jsonschema.validate(instance=document, schema=schema)


def generate_flow(
    *,
    input_path: pathlib.Path,
    schema_path: pathlib.Path,
    model: str,
    use_stub: Optional[pathlib.Path] = None,
    skip_validation: bool = False,
) -> FlowDocument:
    schema = load_schema(schema_path)
    input_text = input_path.read_text(encoding="utf-8")
    prompt = build_prompt(input_text)

    if use_stub:
        client: LLMClient = DummyLLMClient(use_stub)
    else:
        client = create_llm_client()

    provider = detect_provider() if not use_stub else None

    raw = client.structured_flow(prompt=prompt, schema=schema, model=model)
    raw = normalize_flow_document(raw)
    if provider:
        metadata = raw.setdefault("metadata", {})
        metadata["generation"] = {"model": model, "provider": provider}
    if not skip_validation:
        validate(raw, schema)
    return FlowDocument(**raw)


def save_output(document: FlowDocument, output_path: pathlib.Path) -> None:
    output_path.write_text(json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Layer1 flow JSON via LLM.")
    parser.add_argument("--input", type=pathlib.Path, required=True, help="入力テキストファイル")
    parser.add_argument("--schema", type=pathlib.Path, default=pathlib.Path("schemas/flow.schema.json"))
    parser.add_argument("--model", type=str, default="gpt-4.1-mini")
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("output/flow.json"))
    parser.add_argument("--stub", type=pathlib.Path, help="LLM を呼ばずサンプル JSON を読み込む場合に指定")
    parser.add_argument("--skip-validation", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = generate_flow(
        input_path=args.input,
        schema_path=args.schema,
        model=args.model,
        use_stub=args.stub,
        skip_validation=args.skip_validation,
    )
    save_output(document, args.output)
    print(f"[layer1] flow JSON を {args.output} に保存しました。")


if __name__ == "__main__":
    main()
