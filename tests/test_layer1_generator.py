from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Tuple

from src.layer1 import flow_json_generator as layer1_generator
from src.layer1.flow_json_generator import FlowDocument, generate_flow, normalize_flow_document
from src.llm_client_builder import is_dummy_value


def _load_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_flow_matches_expected(layer1_sample_case: Tuple[str, Path, Path], schema_path: Path) -> None:
    """
    Layer1 ジェネレーターがスタブ JSON と一致することを確認する。
    """

    _, input_path, expected_path = layer1_sample_case

    document: FlowDocument = generate_flow(
        input_path=input_path,
        schema_path=schema_path,
        model="gpt-4.1-mini",
        use_stub=expected_path,
    )

    assert document.to_dict() == _load_expected(expected_path)


def test_normalize_flow_document_llm_sample(llm_raw_sample: Dict[str, object]) -> None:
    normalized = normalize_flow_document(llm_raw_sample)

    actor_ids = {actor["id"] for actor in normalized["actors"]}
    phase_ids = {phase["id"] for phase in normalized["phases"]}

    assert actor_ids
    assert phase_ids

    for task in normalized["tasks"]:
        assert "actor_id" in task and task["actor_id"] in actor_ids
        assert "phase_id" in task and task["phase_id"] in phase_ids
        assert isinstance(task["handoff_to"], list)

    assert set(normalized["metadata"].keys()) == {"id", "title", "source", "last_updated"}

    assert normalized["issues"], "issues should be preserved"
    assert "severity" not in normalized["issues"][0]


def test_is_dummy_value_variations() -> None:
    assert is_dummy_value("XXX-placeholder")
    assert is_dummy_value("your-key-here")
    assert not is_dummy_value("sk-proj--live-123456789")
    assert is_dummy_value("short")
    assert not is_dummy_value("live-valid-key-123")


def test_cleanup_dummy_proxies(monkeypatch) -> None:
    from src.llm_client_builder import cleanup_dummy_proxies

    monkeypatch.setenv("HTTP_PROXY", "http://XXX.XX.X.XX:XXXX")
    monkeypatch.setenv("HTTPS_PROXY", "http://valid.proxy:8080")

    cleanup_dummy_proxies()

    assert "HTTP_PROXY" not in os.environ
    assert os.environ["HTTPS_PROXY"] == "http://valid.proxy:8080"


def test_detect_provider_prefers_azure(monkeypatch) -> None:
    import src.llm_client_builder as llm_builder

    monkeypatch.setattr(llm_builder, "_PROVIDER_CACHE", None, raising=False)
    monkeypatch.setattr(llm_builder, "_PROVIDER_ERRORS", [], raising=False)
    monkeypatch.setattr(llm_builder, "validate_azure_env", lambda: True)
    monkeypatch.setattr(llm_builder, "test_azure_available", lambda: True)
    monkeypatch.setattr(llm_builder, "validate_openai_env", lambda: True)
    monkeypatch.setattr(llm_builder, "test_openai_available", lambda: True)

    assert llm_builder.detect_provider() == "azure"


def test_detect_provider_handles_missing_env(monkeypatch) -> None:
    import src.llm_client_builder as llm_builder

    monkeypatch.setattr(llm_builder, "_PROVIDER_CACHE", None, raising=False)
    monkeypatch.setattr(llm_builder, "_PROVIDER_ERRORS", [], raising=False)
    monkeypatch.setattr(llm_builder, "validate_azure_env", lambda: False)
    monkeypatch.setattr(llm_builder, "test_azure_available", lambda: False)
    monkeypatch.setattr(llm_builder, "validate_openai_env", lambda: False)
    monkeypatch.setattr(llm_builder, "test_openai_available", lambda: False)

    assert llm_builder.detect_provider() is None
    assert llm_builder._PROVIDER_ERRORS  # type: ignore[attr-defined]


def test_generate_flow_records_generation_metadata(monkeypatch, tmp_path: Path, schema_path: Path) -> None:
    import src.llm_client_builder as llm_builder

    monkeypatch.setattr(llm_builder, "_PROVIDER_CACHE", None, raising=False)
    monkeypatch.setattr(llm_builder, "_PROVIDER_ERRORS", [], raising=False)

    class FakeClient:
        def structured_flow(self, *, prompt: str, schema: Dict[str, object], model: str) -> Dict[str, object]:
            _ = prompt, schema, model
            return {
                "actors": [{"id": "actor_1", "name": "Sales"}],
                "phases": [{"id": "phase_1", "name": "Plan"}],
                "tasks": [
                    {
                        "id": "task_1",
                        "name": "Review request",
                        "actor_id": "actor_1",
                        "phase_id": "phase_1",
                    }
                ],
                "flows": [{"id": "flow_1", "from": "task_1", "to": "task_1"}],
                "issues": [{"id": "issue_1", "note": "none"}],
                "metadata": {
                    "id": "flow_1",
                    "title": "Demo",
                    "source": "tests/data/demo.md",
                    "last_updated": "2025-01-01",
                },
            }

    monkeypatch.setattr(llm_builder, "create_llm_client", lambda: FakeClient())
    monkeypatch.setattr(llm_builder, "detect_provider", lambda: "openai")

    input_path = tmp_path / "input.md"
    input_path.write_text("demo input", encoding="utf-8")

    document = generate_flow(
        input_path=input_path,
        schema_path=schema_path,
        model="gpt-test",
        use_stub=None,
        skip_validation=True,
    )

    assert document.metadata is not None
    assert document.metadata["generation"] == {"model": "gpt-test", "provider": "openai"}
