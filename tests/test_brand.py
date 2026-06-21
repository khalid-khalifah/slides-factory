"""Edge cases for brand YAML loading (no MIM theme dependency)."""

from __future__ import annotations

from pathlib import Path

import pytest

from slides_factory.brand import (
    BrandColor,
    BrandColors,
    PageSpec,
    load_brand,
)
from slides_factory.brand.theme import resolve_color, resolve_contrast


def _pair(color: str, contrast: str) -> dict[str, str]:
    return {"color": color, "contrast": contrast}


def test_brand_colors_normalize_hex():
    colors = BrandColors.model_validate(
        {
            "main": [_pair("413259", "ffffff")],
            "secondary": [],
            "basic": [_pair("ffffff", "000000")],
        }
    )
    assert colors.main[0].color == "#413259"
    assert colors.main[0].contrast == "#FFFFFF"
    assert colors.basic[0].color == "#FFFFFF"


def test_brand_colors_reject_plain_hex():
    with pytest.raises(ValueError, match="color.*contrast"):
        BrandColors.model_validate({"main": ["#111111"], "secondary": [], "basic": []})


def test_resolve_color_and_contrast(tmp_path: Path):
    path = tmp_path / "brand.yaml"
    path.write_text(
        """
name: acme
default_frame: plain
colors:
  main:
    - color: "#111111"
      contrast: "#EEEEEE"
""",
        encoding="utf-8",
    )
    theme = load_brand(path)
    assert resolve_color(theme, "main", 0) == "#111111"
    assert resolve_contrast(theme, "main", 0) == "#EEEEEE"


def test_page_spec_defaults():
    page = PageSpec.model_validate({})
    assert page.width_in == 10.0
    assert page.height_in == 7.5


def test_load_brand_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        load_brand(missing)


def test_load_brand_flat_font_paths(tmp_path: Path):
    font = tmp_path / "fonts" / "body.ttf"
    font.parent.mkdir(parents=True)
    font.write_bytes(b"")
    path = tmp_path / "brand.yaml"
    path.write_text(
        f"""
name: acme
default_frame: plain
colors:
  main:
    - color: "#111111"
      contrast: "#FFFFFF"
fonts:
  title: fonts/body.ttf
  body: fonts/body.ttf
""",
        encoding="utf-8",
    )
    theme = load_brand(path)
    assert theme.fonts.slots["body"].file == Path("fonts/body.ttf")
    assert theme.fonts.slots["title"].file == Path("fonts/body.ttf")


def test_load_brand_legacy_nested_fonts(tmp_path: Path):
    path = tmp_path / "brand.yaml"
    path.write_text(
        """
name: acme
default_frame: plain
colors:
  main:
    - color: "#111111"
      contrast: "#FFFFFF"
fonts:
  body:
    family: Helvetica
""",
        encoding="utf-8",
    )
    theme = load_brand(path)
    assert theme.fonts.family_for(theme, "body") == "Helvetica"


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
  main:
    - color: "#111111"
      contrast: "#FFFFFF"
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
    theme = load_brand(path)
    assert theme.name == "acme"
    assert theme.default_frame == "plain"
    assert theme.colors.main[0] == BrandColor(color="#111111", contrast="#FFFFFF")
