"""Test-only text element — wraps the text converter so templates can use @at(kind="text")."""

from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.converters.text import TextBlock, render_text_block
from slides_factory.elements.base import Box
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme
from tests.fixtures.app import app


class TextProps(BaseModel):
    block: TextBlock = TextBlock(children=[])


class TextStyle(BaseModel):
    text_size: str = "base"
    text_color: str = "primary"
    bold: bool = False
    align: str = "left"
    font: str = "body"


@app.element("text", props_model=TextProps, style_model=TextStyle)
def render_text(
    slide: Slide,
    box: Box,
    props: TextProps,
    style: TextStyle,
    ctx: RenderContext,
) -> None:
    """Render rich text into a grid cell via the text converter."""
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
