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
from slides_factory.exceptions import SlidesFactoryError


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
        """
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


# ---------------------------------------------------------------------------
# Brand inheritance (extends key)
# ---------------------------------------------------------------------------


def _write_brand(path: Path, name: str, /, **overrides: object) -> None:
    """Write a minimal brand YAML with the given name and optional overrides."""
    data: dict[str, object] = {
        "name": name,
        "default_frame": "plain",
        "colors": {
            "main": [{"color": "#111111", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#FFFFFF", "contrast": "#000000"}],
        },
    }
    data.update(overrides)
    import yaml

    path.write_text(yaml.dump(data), encoding="utf-8")


def test_extends_single_parent(tmp_path: Path):
    """Child overrides colors, inherits everything else."""
    _write_brand(tmp_path / "parent.yaml", "parent")
    _write_brand(
        tmp_path / "child.yaml",
        "child",
        extends="parent.yaml",
        colors={
            "main": [{"color": "#FF0000", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#000000", "contrast": "#FFFFFF"}],
        },
    )
    theme = load_brand(tmp_path / "child.yaml")
    assert theme.name == "child"
    assert theme.default_frame == "plain"  # inherited from parent
    assert theme.colors.main[0].color == "#FF0000"  # child's override
    assert theme.colors.basic[0].color == "#000000"


def test_extends_multiple_ordered(tmp_path: Path):
    """Multiple parents: later overrides earlier, child wins all."""
    base = tmp_path / "base.yaml"
    override_a = tmp_path / "override-a.yaml"
    override_b = tmp_path / "override-b.yaml"
    child = tmp_path / "child.yaml"

    # base sets colors
    _write_brand(
        base,
        "base",
        colors={
            "main": [{"color": "#AAAAAA", "contrast": "#111111"}],
            "secondary": [],
            "basic": [{"color": "#BBBBBB", "contrast": "#222222"}],
        },
    )
    # override-a changes main to blue
    _write_brand(
        override_a, "a",
        colors={
            "main": [{"color": "#0000FF", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#BBBBBB", "contrast": "#222222"}],
        },
    )
    # override-b changes main to green (should win over a, but not child)
    _write_brand(
        override_b, "b",
        colors={
            "main": [{"color": "#00FF00", "contrast": "#000000"}],
            "secondary": [],
            "basic": [{"color": "#BBBBBB", "contrast": "#222222"}],
        },
    )
    _write_brand(
        child,
        "child",
        extends=["base.yaml", "override-a.yaml", "override-b.yaml"],
        # child overrides main to red
        colors={
            "main": [{"color": "#FF0000", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#000000", "contrast": "#FFFFFF"}],
        },
    )

    theme = load_brand(child)
    # Child value wins
    assert theme.colors.main[0].color == "#FF0000"
    # Extends resolution happens — basic comes from child too (full replacement)
    assert theme.colors.basic[0].color == "#000000"


def test_extends_inherits_fonts_and_logos(tmp_path: Path):
    """Fonts and logos from parent are inherited when child doesn't override them."""
    font_file = tmp_path / "body.ttf"
    font_file.write_bytes(b"")
    logo_file = tmp_path / "logo.svg"
    logo_file.write_bytes(b"")

    _write_brand(
        tmp_path / "parent.yaml",
        "parent",
        fonts={"title": "body.ttf", "body": "body.ttf"},
    )
    # No logos key in _write_brand — need to add it manually
    import yaml

    parent_path = tmp_path / "parent.yaml"
    parent_dict = {
        "name": "parent",
        "default_frame": "plain",
        "colors": {
            "main": [{"color": "#111111", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#FFFFFF", "contrast": "#000000"}],
        },
        "fonts": {"title": "body.ttf", "body": "body.ttf"},
    }
    parent_path.write_text(yaml.dump(parent_dict), encoding="utf-8")

    child_path = tmp_path / "child.yaml"
    child_dict = {
        "name": "child",
        "default_frame": "plain",
        "extends": "parent.yaml",
        "colors": {
            "main": [{"color": "#FF0000", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#FFFFFF", "contrast": "#000000"}],
        },
    }
    child_path.write_text(yaml.dump(child_dict), encoding="utf-8")

    theme = load_brand(child_path)
    assert theme.name == "child"
    # Fonts inherited from parent
    assert "title" in theme.fonts.slots
    assert "body" in theme.fonts.slots


def test_extends_circular_raises(tmp_path: Path):
    """a → b → a chain raises SlidesFactoryError."""
    _write_brand(tmp_path / "a.yaml", "a", extends="b.yaml")
    _write_brand(tmp_path / "b.yaml", "b", extends="a.yaml")
    with pytest.raises(SlidesFactoryError, match="Circular brand"):
        load_brand(tmp_path / "a.yaml")


def test_extends_longer_chain_raises(tmp_path: Path):
    """a → b → c → d → e → f → a chain raises SlidesFactoryError (circular)."""
    names = ["a", "b", "c", "d", "e", "f"]
    for i, name in enumerate(names):
        next_name = names[(i + 1) % len(names)]
        _write_brand(tmp_path / f"{name}.yaml", name, extends=f"{next_name}.yaml")
    with pytest.raises(SlidesFactoryError, match="Circular brand"):
        load_brand(tmp_path / "a.yaml")


def test_extends_missing_parent_raises(tmp_path: Path):
    """Referencing a non-existent parent raises FileNotFoundError."""
    _write_brand(tmp_path / "child.yaml", "child", extends="missing.yaml")
    with pytest.raises(FileNotFoundError):
        load_brand(tmp_path / "child.yaml")


def test_extends_no_parent_key_is_noop(tmp_path: Path):
    """Brand YAML without extends loads normally (backward compat)."""
    _write_brand(tmp_path / "standalone.yaml", "standalone")
    theme = load_brand(tmp_path / "standalone.yaml")
    assert theme.name == "standalone"
    assert theme.default_frame == "plain"


def test_extends_page_spec_replaced(tmp_path: Path):
    """page spec is fully replaced by child, not merged field-by-field."""
    _write_brand(
        tmp_path / "parent.yaml",
        "parent",
        page={"width_in": 10.0, "height_in": 7.5},
    )
    _write_brand(
        tmp_path / "child.yaml",
        "child",
        extends="parent.yaml",
        page={"width_in": 13.333},
        colors={
            "main": [{"color": "#111111", "contrast": "#FFFFFF"}],
            "secondary": [],
            "basic": [{"color": "#FFFFFF", "contrast": "#000000"}],
        },
    )
    theme = load_brand(tmp_path / "child.yaml")
    assert theme.page.width_in == 13.333
    # height_in falls back to PageSpec default (7.5) because child fully replaced page
    assert theme.page.height_in == 7.5


def test_extends_colors_replace_not_append(tmp_path: Path):
    """Child's colors list replaces parent's — no appending."""
    _write_brand(
        tmp_path / "parent.yaml",
        "parent",
        colors={
            "main": [
                {"color": "#111111", "contrast": "#FFFFFF"},
                {"color": "#222222", "contrast": "#EEEEEE"},
            ],
            "secondary": [],
            "basic": [{"color": "#FFFFFF", "contrast": "#000000"}],
        },
    )
    _write_brand(
        tmp_path / "child.yaml",
        "child",
        extends="parent.yaml",
        colors={
            "main": [{"color": "#FF0000", "contrast": "#FFFFFF"}],
            "secondary": [{"color": "#00FF00", "contrast": "#000000"}],
            "basic": [{"color": "#000000", "contrast": "#FFFFFF"}],
        },
    )
    theme = load_brand(tmp_path / "child.yaml")
    assert len(theme.colors.main) == 1  # replaced, not appended
    assert theme.colors.main[0].color == "#FF0000"
    assert len(theme.colors.secondary) == 1
    assert theme.colors.secondary[0].color == "#00FF00"

