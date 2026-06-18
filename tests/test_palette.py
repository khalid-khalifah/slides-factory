"""Tests for brand-derived slide palettes."""

from __future__ import annotations

from slides_factory.brand import load_brand
from slides_factory.palette import palette_from_brand_surface


def test_palette_from_brand_surface_maps_text_to_contrast(minimal_brand_yaml):
    brand = load_brand(minimal_brand_yaml)
    palette = palette_from_brand_surface(
        brand,
        group="main",
        index=1,
        highlight_group="main",
        highlight_index=0,
    )
    assert palette.text == "#1A1A1A"
    assert palette.main[0] == "#E6E6E6"
    assert palette.highlight == "#413258"
