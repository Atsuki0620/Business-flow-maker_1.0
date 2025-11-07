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
import pathlib
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Protocol

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
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
        response = self._client.responses.create(
            model=model,
            input=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "FlowSchema", "schema": schema},
            },
        )
        content = response.output[0].content[0].text if response.output else "{}"
        return json.loads(content)


class DummyLLMClient:
    """Simple client that loads a pre-built JSON file for offline testing."""

    def __init__(self, stub_path: pathlib.Path) -> None:
        self._stub_path = stub_path

    def structured_flow(self, *, prompt: str, schema: Dict[str, Any], model: str) -> Dict[str, Any]:
        _ = prompt, schema, model
        return json.loads(self._stub_path.read_text(encoding="utf-8"))


def load_schema(schema_path: pathlib.Path) -> Dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def build_prompt(input_text: str) -> str:
    return (
        "あなたは業務フローアーキテクトです。以下の入力を読み、"
        "actors / phases / tasks / flows / gateways / issues / metadata を含む JSON を生成してください。\n\n"
        f"--- INPUT START ---\n{input_text}\n--- INPUT END ---\n\n"
        "必須ルール:\n"
        "1. JSON Schema に準拠し、snake_case キーを維持する。\n"
        "2. 曖昧または不明な情報は issues[].note に記録し、UNKNOWN という語を含める。\n"
        "3. flows[].condition は必要な場合のみ記載する。\n"
        "4. tasks[].handoff_to は空配列でも必ず含める。\n"
    )


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
        client = OpenAILLMClient()

    raw = client.structured_flow(prompt=prompt, schema=schema, model=model)
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
