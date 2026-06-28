"""Text element — a rich text box placed in a grid cell.

This is a thin wrapper over ``slides_factory/converters/text.py``.
The low-level ``render_text_block()`` converter works on any
python-pptx ``TextFrame`` (shape, textbox, table cell, …).
"""

from __future__ import annotations

from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.elements.base import Box
from slides_factory.elements.text.model import TextBlock
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme
from slides_factory.styling.models import TextStyle


class TextProps(BaseModel):
    """Content props for the text element.

    ``block`` holds the rich-text document tree.  Element-level styling is
    passed through the separate ``style`` parameter (the element's
    ``style_model``), not embedded in props.
    """

    block: TextBlock = TextBlock(children=[])


def render_text(
    slide: Slide,
    box: Box,
    props: TextProps,
    style: TextStyle,
    ctx: RenderContext,
) -> None:
    """Render rich text content into the given grid-cell box."""
    from slides_factory.converters.text import render_text_block

    textbox = slide.shapes.add_textbox(*box)
    render_text_block(
        props.block,
        textbox.text_frame,
        ctx,
        base_size_pt=theme.font_size_pt(style.text_size),
        base_color=style.text_color,
        base_bold=style.bold,
        alignment=style.align,
        font_slot=style.font,
        vertical_anchor="top",
    )
