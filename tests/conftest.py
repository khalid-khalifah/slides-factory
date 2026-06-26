"""Core test harness — isolated SlideFactory with minimal fixtures (no mim_slides)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.app import app as _core_app


@pytest.fixture
def app():
    """Return the test-core SlideFactory instance."""
    return _core_app


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
  main:
    - color: "#413258"
      contrast: "#FFFFFF"
    - color: "#E6E6E6"
      contrast: "#1A1A1A"
  secondary: []
  basic:
    - color: "#FFFFFF"
      contrast: "#000000"
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
