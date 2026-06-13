"""Core test harness — isolated SlideFactory with minimal fixtures (no mim_slides)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import slides_factory.app as app_module


@pytest.fixture(autouse=True)
def _activate_core_app():
    """Ensure core tests always use the test-core catalog."""
    core_app_module = importlib.import_module("tests.fixtures.app")
    app_module._active_app = core_app_module.app
    yield


@pytest.fixture
def minimal_brand_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "brand.yaml"
    path.write_text(
        """
name: test
default_frame: plain
page:
  width_in: 10
  height_in: 7.5
colors:
  main: ["#413258", "#E6E6E6"]
  secondary: []
  basic: ["#FFFFFF"]
layout:
  logos:
    en:
      left: 10
      top: 5
      width: 20
logos: {}
""",
        encoding="utf-8",
    )
    return path
