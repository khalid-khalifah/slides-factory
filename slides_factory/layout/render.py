"""Core grid rendering primitive.

``render_layout`` is the foundation the whole engine draws through: given a
:class:`Layout` (grid classes + cells, each holding an element) it solves the
grid inside the frame's playground and renders every element. Both the raw
flag-driven builder and class-based templates render through this function —
templates simply *produce* a Layout and hand it here.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from pptx.slide import Slide

from slides_factory.frame import DEFAULT_PLAYGROUND
from slides_factory.layout.grid import compute_cells
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout_spec import Layout
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import parse_cell, parse_element, parse_grid

_ALIGN_X_TO_TEXT = {"start": "left", "center": "center", "end": "right"}


def render_layout(slide: Slide, layout: Layout, ctx: RenderContext) -> None:
    """Draw a Layout into the frame playground (or a default region)."""
    from slides_factory.app import get_app

    app = get_app()

    region = ctx.playground or resolve_pct_box(ctx, DEFAULT_PLAYGROUND)
    grid_style = parse_grid(layout.grid)
    cell_styles = [parse_cell(cell.at) for cell in layout.cells]
    placed = compute_cells(region, grid_style, cell_styles, rtl=ctx.rtl)

    for cell_style, placement, cell in zip(cell_styles, placed, layout.cells):
        element = app.get_element(cell.element.kind)
        element_style = parse_element(cell.element.style)
        element_style = _inherit_cell_alignment(element_style, cell_style)
        props = element.validate_props(cell.element.props)
        element.render(slide, placement.box, element_style, props, ctx)


def _inherit_cell_alignment(element_style: Any, cell_style: Any):
    """Let cell ``items-*`` / ``justify-*`` fill in element valign / align."""
    valign = element_style.valign
    align = element_style.align
    if valign is None and cell_style.align_y != "stretch":
        valign = cell_style.align_y
    if align is None and cell_style.align_x != "stretch":
        align = _ALIGN_X_TO_TEXT.get(cell_style.align_x)
    return replace(element_style, valign=valign, align=align)
