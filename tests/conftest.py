"""
Common pytest fixtures for Business-flow-maker tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "flow.schema.json"

SAMPLE_CASES: Tuple[Tuple[str, Path, Path], ...] = (
    (
        "small",
        PROJECT_ROOT / "samples" / "input" / "sample-small-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-small-01.json",
    ),
    (
        "medium",
        PROJECT_ROOT / "samples" / "input" / "sample-medium-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-medium-01.json",
    ),
    (
        "large",
        PROJECT_ROOT / "samples" / "input" / "sample-large-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-large-01.json",
    ),
)


@pytest.fixture(scope="session")
def schema_path() -> Path:
    return SCHEMA_PATH


@pytest.fixture(params=SAMPLE_CASES, ids=lambda case: case[0])
def layer1_sample_case(request: pytest.FixtureRequest) -> Iterator[Tuple[str, Path, Path]]:
    yield request.param
