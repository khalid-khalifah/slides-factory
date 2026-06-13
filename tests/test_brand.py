"""Edge cases for brand YAML loading (no MIM theme dependency)."""

from __future__ import annotations

from pathlib import Path

import pytest

from slides_factory.brand import BrandColors, PageSpec, load_brand


def test_brand_colors_normalize_hex():
    colors = BrandColors.model_validate(
        {"main": ["413259"], "secondary": [], "basic": ["ffffff"]}
    )
    assert colors.main[0] == "#413259"
    assert colors.basic[0] == "#FFFFFF"


def test_page_spec_defaults():
    page = PageSpec.model_validate({})
    assert page.width_in == 10.0
    assert page.height_in == 7.5


def test_load_brand_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        load_brand(missing)


def test_load_brand_minimal_yaml(tmp_path: Path):
    path = tmp_path / "brand.yaml"
    path.write_text(
        """
name: acme
default_frame: plain
page:
  width_in: 10
  height_in: 7.5
colors:
  main: ["#111111"]
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
    theme = load_brand(path)
    assert theme.name == "acme"
    assert theme.default_frame == "plain"
    assert theme.colors.main[0] == "#111111"
