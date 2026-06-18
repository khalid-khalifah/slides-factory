"""Tests for the styling engine: theme scale and utility-class parser."""

from __future__ import annotations

import pytest

from slides_factory.palette import SlidePalette
from slides_factory.styling import theme
from slides_factory.styling.tokens import parse_cell, parse_grid


# --- theme scale ----------------------------------------------------------


def test_spacing_resolves_known_step():
    assert theme.spacing(4) == 0.05
    assert theme.spacing(0) == 0.0


def test_spacing_rejects_unknown_step():
    with pytest.raises(ValueError, match="unknown spacing step"):
        theme.spacing(7)


def test_font_size_and_radius_scales():
    assert theme.font_size_pt("2xl") == 32.0
    assert theme.radius("md") == 0.10
    with pytest.raises(ValueError, match="unknown font size"):
        theme.font_size_pt("huge")


def test_color_token_uses_palette_then_fallback():
    palette = SlidePalette(
        text="#101010", highlight="#202020", main=("#303030",), extras=("#404040",)
    )
    assert theme.resolve_color_token("primary", palette) == "#101010"
    assert theme.resolve_color_token("highlight", palette) == "#202020"
    assert theme.resolve_color_token("surface", palette) == "#303030"
    assert theme.resolve_color_token("muted", palette) == "#404040"
    # No palette -> neutral fallback.
    assert theme.resolve_color_token("primary", None) == "#111111"


def test_color_token_rejects_unknown():
    with pytest.raises(ValueError, match="unknown color token"):
        theme.resolve_color_token("brandY", None)


def test_resolve_style_color_brand_refs(minimal_brand_yaml, tmp_path):
    from slides_factory.brand import load_brand
    from slides_factory.render_context import RenderContext

    brand = load_brand(minimal_brand_yaml)
    ctx = RenderContext(
        rtl=False,
        locale="en",
        slide_width=1,
        slide_height=1,
        brand=brand,
    )
    assert theme.resolve_style_color("main:0", ctx) == "#413258"
    assert theme.resolve_style_color("on-main:0", ctx) == "#FFFFFF"
    assert theme.resolve_style_color("on-main:1", ctx) == "#1A1A1A"


# --- grid parser ----------------------------------------------------------


def test_parse_grid_equal_columns():
    style = parse_grid("grid-cols-3")
    assert style.columns == (1.0, 1.0, 1.0)
    assert style.rows == (1.0,)


def test_parse_grid_ratio_tracks():
    style = parse_grid("grid-cols-[2_1_1] grid-rows-[1_2]")
    assert style.columns == (2.0, 1.0, 1.0)
    assert style.rows == (1.0, 2.0)


def test_parse_grid_gaps_and_padding():
    style = parse_grid("gap-x-4 gap-y-2 px-6 py-8")
    assert style.col_gap == theme.spacing(4)
    assert style.row_gap == theme.spacing(2)
    assert style.pad_x == theme.spacing(6)
    assert style.pad_y == theme.spacing(8)


def test_parse_grid_uniform_gap_and_padding():
    style = parse_grid("gap-4 p-2")
    assert style.col_gap == style.row_gap == theme.spacing(4)
    assert style.pad_x == style.pad_y == theme.spacing(2)


def test_parse_grid_rejects_unknown_token():
    with pytest.raises(ValueError, match="unknown grid utility class"):
        parse_grid("text-lg")


# --- cell parser ----------------------------------------------------------


def test_parse_cell_spans_and_starts():
    style = parse_cell("col-span-2 row-span-3 col-start-1 row-start-2")
    assert (style.col_span, style.row_span) == (2, 3)
    assert (style.col_start, style.row_start) == (1, 2)


def test_parse_cell_alignment():
    style = parse_cell("items-center justify-end")
    assert style.align_y == "center"
    assert style.align_x == "end"


def test_parse_cell_rejects_unknown_and_bad_values():
    with pytest.raises(ValueError, match="unknown cell utility class"):
        parse_cell("text-lg")
    with pytest.raises(ValueError, match=">= 1"):
        parse_cell("col-span-0")

