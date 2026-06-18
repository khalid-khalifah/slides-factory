"""Card element — a filled rounded box with stat text."""

from __future__ import annotations

from pydantic import BaseModel
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.slide import Slide

from slides_factory.brand import hex_to_rgb
from slides_factory.elements.base import Box, style_paragraph
from slides_factory.layout.fonts import apply_shape_font
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme


class CardProps(BaseModel):
    """Props for the card element."""

    title: str = ""
    value: str = ""
    body: str = ""


def render_card(
    slide: Slide,
    box: Box,
    props: CardProps,
    ctx: RenderContext,
) -> None:
    """Render a filled card with optional title / value / body text."""
    left, top, width, height = box
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )

    if shape.adjustments:
        shape.adjustments[0] = min(0.5, max(0.0, theme.radius("md")))

    shape.fill.solid()
    shape.fill.fore_color.rgb = hex_to_rgb(
        theme.resolve_color_token("surface", ctx.palette)
    )
    shape.line.fill.background()

    frame = shape.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    rows: list[tuple[str, float, bool, str]] = []
    if props.title:
        rows.append((props.title, theme.font_size_pt("sm"), False, "muted"))
    if props.value:
        rows.append((props.value, theme.font_size_pt("2xl"), True, "primary"))
    if props.body:
        rows.append((props.body, theme.font_size_pt("base"), False, "primary"))
    if not rows:
        rows.append(("", theme.font_size_pt("base"), False, "primary"))

    for index, (content, size_pt, bold, color_token) in enumerate(rows):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = content
        style_paragraph(
            paragraph,
            ctx,
            size_pt=size_pt,
            bold=bold,
            color_token=color_token,
            align="center",
        )

    apply_shape_font(shape, ctx)
