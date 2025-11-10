"""
Flow JSON generator for Layer1 (LLM-friendly draft).

This module provides:
- dataclass representations for the schema
- flow generation logic and normalization
- JSON Schema validation helper
- CLI entry point for local runs
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from src.core.llm_client import LLMClient, create_llm_client, detect_provider

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
    base = (
        "あなたは業務フローアーキテクトです。以下の入力を読み、"
        "actors / phases / tasks / flows / gateways / issues / metadata を含む JSON を生成してください。\n"
        f"--- INPUT START ---\n{input_text}\n--- INPUT END ---\n\n"
        "必須ルール:\n"
        "1. JSON Schema に準拠し、snake_case キーを維持する。\n"
        "2. 曖昧または不明な情報は issues[].note に記録し、UNKNOWN として扱わず含める。\n"
        "3. flows[].condition は必要な場合のみ記載する。\n"
        "4. tasks[].handoff_to は空配列でも必ず含める。\n"
    )
    extras = (
        "5. actors[].id とタスク[].actor_id は全てのアクターIDを使用する。\n"
        "6. metadata は、id/title/source/last_updated のみを利用する。\n"
        "7. 出力は ``` などを含まないで純粋なJSONを返す。\n"
    )
    return base + extras



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
    if not isinstance(metadata, dict):
        metadata = {}

    # LLM出力でトップレベルに混在したメタ情報を拾い上げる
    legacy_keys = ("id", "title", "source", "last_updated")
    for key in legacy_keys:
        value = data.pop(key, None)
        if value and key not in metadata:
            metadata[key] = value

    generation_info = metadata.get("generation") if isinstance(metadata.get("generation"), dict) else None

    today = date.today().isoformat()
    data["metadata"] = {
        "id": metadata.get("id", "sample-flow"),
        "title": metadata.get("title", metadata.get("name", "LLM generated flow")),
        "source": metadata.get("source", "samples/input/sample-small-01.md"),
        "last_updated": metadata.get("last_updated", today),
    }
    if generation_info:
        data["metadata"]["generation"] = generation_info

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
    parser.add_argument("--output", type=pathlib.Path, default=None, help="出力先（省略時は runs/ 配下に自動生成）")
    parser.add_argument("--stub", type=pathlib.Path, help="LLM を呼ばずサンプル JSON を読み込む場合に指定")
    parser.add_argument("--skip-validation", action="store_true")
    return parser.parse_args()


def main() -> None:
    import sys
    import time
    from src.utils import run_manager

    args = parse_args()
    start_time = time.time()

    # 出力先の決定
    if args.output is None:
        # runs/構造を使用
        run_dir = run_manager.create_run_dir(args.input)
        run_manager.copy_input_file(args.input, run_dir)
        output_path = run_dir / "output" / "flow.json"
        use_runs = True
    else:
        # 従来の出力先を使用
        output_path = args.output
        run_dir = None
        use_runs = False

    # JSON生成
    document = generate_flow(
        input_path=args.input,
        schema_path=args.schema,
        model=args.model,
        use_stub=args.stub,
        skip_validation=args.skip_validation,
    )
    save_output(document, output_path)

    elapsed_time = time.time() - start_time
    print(f"[layer1] flow JSON を {output_path} に保存しました。")

    # runs/構造を使用した場合は info.md を生成
    if use_runs and run_dir:
        # 基本情報
        info = {
            "execution_id": run_dir.name,
            "execution_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "command": " ".join(sys.argv),
            "input_file": str(args.input),
            "input_size": args.input.stat().st_size,
            "input_hash": run_manager._calculate_file_hash(args.input),
        }

        # 生成設定
        if not args.stub:
            info["model"] = args.model
            provider = detect_provider()
            if provider:
                info["provider"] = provider
        info["elapsed_time"] = elapsed_time

        # 出力ファイル
        info["output_files"] = [
            {"path": str(output_path.relative_to(run_dir)), "size": output_path.stat().st_size}
        ]

        run_manager.save_info_md(run_dir, info)

        # JSON検証結果を追記
        doc_dict = document.to_dict()
        validation = {
            "actors_count": len(doc_dict.get("actors", [])),
            "phases_count": len(doc_dict.get("phases", [])),
            "tasks_count": len(doc_dict.get("tasks", [])),
            "flows_count": len(doc_dict.get("flows", [])),
            "gateways_count": len(doc_dict.get("gateways", [])),
            "issues_count": len(doc_dict.get("issues", [])),
        }
        run_manager.update_info_md(run_dir, {"json_validation": validation})

        print(f"[layer1] 実行情報を {run_dir / 'info.md'} に記録しました。")


if __name__ == "__main__":
    main()
