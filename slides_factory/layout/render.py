"""Core grid rendering primitive.

``render_layout`` is the foundation the whole engine draws through: given a
:class:`Layout` (grid classes + cells, each holding an element) it solves the
grid inside the frame's playground and renders every element. Both the raw
flag-driven builder and class-based templates render through this function —
templates simply *produce* a Layout and hand it here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pptx.slide import Slide

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory
from slides_factory.frame import DEFAULT_PLAYGROUND
from slides_factory.layout.grid import compute_cells
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout_spec import Layout
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import parse_cell, parse_grid


def render_layout(
    slide: Slide,
    layout: Layout,
    ctx: RenderContext,
    *,
    app: SlideFactory,
) -> None:
    """Draw a Layout into the frame playground (or a default region).

    When ``ctx.debug`` is ``True``, diagnostic shapes (grid lines, cell
    boundaries, labels) are rendered behind the actual content.
    """
    from slides_factory.layout.debug import render_debug_layer

    region = ctx.playground or resolve_pct_box(ctx, DEFAULT_PLAYGROUND)
    grid_style = parse_grid(layout.grid)
    cell_styles = [parse_cell(cell.at) for cell in layout.cells]
    placed = compute_cells(region, grid_style, cell_styles, rtl=ctx.rtl)

    if ctx.debug:
        render_debug_layer(slide, grid_style, placed, ctx=ctx)

    for placement, cell in zip(placed, layout.cells, strict=False):
        if cell.template:
            # Sub-template cell: render the sub-template with the cell's
            # EMU box as its playground.
            sub_template = app.get_template(cell.template)
            sub_data = sub_template.validate_data(cell.cell_data)
            sub_ctx = ctx.with_playground(placement.box)
            sub_template.render(slide, sub_data, sub_ctx)
        else:
            element = app.get_element(cell.element.kind)
            props = element.validate_props(cell.element.props)
            style = element.validate_style(cell.element.style)
            element.render(slide, placement.box, props, style, ctx)
