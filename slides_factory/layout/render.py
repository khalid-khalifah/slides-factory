"""Core grid rendering primitive.

``render_layout`` is the foundation the whole engine draws through: given a
:class:`Layout` (grid classes + cells, each holding an element) it solves the
grid inside the frame's playground and renders every element. Both the raw
flag-driven builder and class-based templates render through this function —
templates simply *produce* a Layout and hand it here.
"""

from __future__ import annotations

from pptx.slide import Slide

from slides_factory.frame import DEFAULT_PLAYGROUND
from slides_factory.layout.grid import compute_cells
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout_spec import Layout
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import parse_cell, parse_grid


def render_layout(slide: Slide, layout: Layout, ctx: RenderContext) -> None:
    """Draw a Layout into the frame playground (or a default region)."""
    from slides_factory.app import get_app

    app = get_app()

    region = ctx.playground or resolve_pct_box(ctx, DEFAULT_PLAYGROUND)
    grid_style = parse_grid(layout.grid)
    cell_styles = [parse_cell(cell.at) for cell in layout.cells]
    placed = compute_cells(region, grid_style, cell_styles, rtl=ctx.rtl)

    for placement, cell in zip(placed, layout.cells):
        element = app.get_element(cell.element.kind)
        props = element.validate_props(cell.element.props)
        element.render(slide, placement.box, props, ctx)
