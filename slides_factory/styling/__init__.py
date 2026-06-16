"""Styling engine — theme scale plus a Tailwind-like utility-class parser.

The engine keeps layout authoring abstract: callers describe grids, cells, and
elements with compact class-token strings (e.g. ``grid-cols-[2_1] gap-4``,
``col-span-2``, ``text-2xl font-bold text-primary``) and the engine resolves
them against a central theme scale.
"""

from slides_factory.styling.theme import (
    FONT_SIZES_PT,
    RADIUS_SCALE,
    SPACING_SCALE,
    resolve_color_token,
)
from slides_factory.styling.tokens import (
    CellStyle,
    ElementStyle,
    GridStyle,
    parse_cell,
    parse_element,
    parse_grid,
)

__all__ = [
    "CellStyle",
    "ElementStyle",
    "FONT_SIZES_PT",
    "GridStyle",
    "RADIUS_SCALE",
    "SPACING_SCALE",
    "parse_cell",
    "parse_element",
    "parse_grid",
    "resolve_color_token",
]
