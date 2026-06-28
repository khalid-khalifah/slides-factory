"""Core grid rendering primitive.

``render_layout`` is the foundation the whole engine draws through: given a
:class:`Layout` (grid classes + cells, each holding an element) it solves the
grid inside the frame's playground and renders every element. Both the raw
flag-driven builder and class-based templates render through this function —
templates simply *produce* a Layout and hand it here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pptx.slide import Slide

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory
    from slides_factory.elements.base import Element
from slides_factory.frame import DEFAULT_PLAYGROUND
from slides_factory.geometry import Box
from slides_factory.layout.grid import compute_cells
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout_spec import Layout
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import parse_cell, parse_grid

logger = logging.getLogger(__name__)


def _check_element_fit(element: Element, box: Box, kind: str) -> None:
    """Warn if *box* violates the element's optional size constraints."""
    if element.min_width is not None and box.width < element.min_width:
        logger.warning(
            "Element %r wider than cell: %d < %d EMU (min_width)",
            kind, box.width, element.min_width,
        )
    if element.max_width is not None and box.width > element.max_width:
        logger.warning(
            "Element %r narrower than cell: %d > %d EMU (max_width)",
            kind, box.width, element.max_width,
        )
    if element.min_height is not None and box.height < element.min_height:
        logger.warning(
            "Element %r taller than cell: %d < %d EMU (min_height)",
            kind, box.height, element.min_height,
        )
    if element.max_height is not None and box.height > element.max_height:
        logger.warning(
            "Element %r shorter than cell: %d > %d EMU (max_height)",
            kind, box.height, element.max_height,
        )


def _check_template_fit(template: object, box: Box, template_id: str) -> None:
    """Warn if *box* violates the sub-template's inferred min/max constraints."""
    min_box = getattr(template, "_min_box", None)
    max_box = getattr(template, "_max_box", None)
    if min_box is not None:
        if callable(min_box):
            min_box = min_box()
        if min_box is not None and (
            box.width < min_box.width or box.height < min_box.height
        ):
            logger.warning(
                "Sub-template %r cell too small: %d×%d < %d×%d EMU (min_box)",
                template_id, box.width, box.height, min_box.width, min_box.height,
            )
    if max_box is not None:
        if callable(max_box):
            max_box = max_box()
        if max_box is not None and (
            box.width > max_box.width or box.height > max_box.height
        ):
            logger.warning(
                "Sub-template %r cell too large: %d×%d > %d×%d EMU (max_box)",
                template_id, box.width, box.height, max_box.width, max_box.height,
            )


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
            sub_template = app.get_template(cell.template)
            sub_data = sub_template.validate_data(cell.cell_data)
            _check_template_fit(sub_template, placement.box, cell.template)
            sub_ctx = ctx.with_playground(placement.box)
            sub_template.render(slide, sub_data, sub_ctx)
        else:
            element = app.get_element(cell.element.kind)
            props = element.validate_props(cell.element.props)
            style = element.validate_style(cell.element.style)
            _check_element_fit(element, placement.box, cell.element.kind)
            element.render(slide, placement.box, props, style, ctx)
