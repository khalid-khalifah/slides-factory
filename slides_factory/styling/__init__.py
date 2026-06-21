"""Styling engine — theme scale, typed style models, and grid/cell parsers."""

# Explicit submodule imports so that ``from slides_factory.styling import theme``
# (and tokens, models) works reliably even if __init__ is refactored.
from slides_factory.styling import (
    models,  # noqa: F401
    theme,  # noqa: F401
    tokens,  # noqa: F401
)
from slides_factory.styling.models import (
    CardStyle,
    EmptyStyle,
    TextStyle,
    resolve_brand_color,
)
from slides_factory.styling.theme import (
    FONT_SIZES_PT,
    RADIUS_SCALE,
    SPACING_SCALE,
    resolve_color_token,
)
from slides_factory.styling.tokens import CellStyle, GridStyle, parse_cell, parse_grid

__all__ = [
    "CardStyle",
    "CellStyle",
    "EmptyStyle",
    "FONT_SIZES_PT",
    "GridStyle",
    "RADIUS_SCALE",
    "SPACING_SCALE",
    "TextStyle",
    "parse_cell",
    "parse_grid",
    "resolve_brand_color",
    "resolve_color_token",
]
