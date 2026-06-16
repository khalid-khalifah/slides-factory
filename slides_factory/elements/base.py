"""Element protocol, registration wrapper, and shared rendering helpers.

Classes:
    Element — Abstract base: a ``kind``, a Pydantic ``props_model``, and render.

Functions:
    element_from_function — Wrap a render function as an Element instance.
    apply_box_padding     — Shrink an EMU box by an element's padding fractions.
    style_paragraph       — Apply size/bold/color/alignment to one paragraph.
    vertical_anchor       — Map a valign token to an MSO anchor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.slide import Slide
from pptx.util import Pt

from slides_factory.render_context import RenderContext
from slides_factory.styling import theme
from slides_factory.styling.tokens import ElementStyle

Box = tuple[int, int, int, int]

_ALIGN_MAP = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}

_ANCHOR_MAP = {
    "start": MSO_ANCHOR.TOP,
    "center": MSO_ANCHOR.MIDDLE,
    "end": MSO_ANCHOR.BOTTOM,
    "stretch": MSO_ANCHOR.TOP,
}


class Element(ABC):
    """Protocol every drawable element implements."""

    kind: ClassVar[str]
    props_model: ClassVar[type[BaseModel]]

    def validate_props(self, props: dict[str, Any]) -> BaseModel:
        """Validate raw props against this element's Pydantic model."""
        return self.props_model.model_validate(props)

    @abstractmethod
    def render(
        self,
        slide: Slide,
        box: Box,
        style: ElementStyle,
        props: BaseModel,
        ctx: RenderContext,
    ) -> None:
        """Draw the element into ``box`` (EMU) using the resolved ``style``."""


def element_from_function(
    func: Callable[..., Any],
    *,
    kind: str,
    props_model: type[BaseModel],
) -> Element:
    """Wrap a render function ``(slide, box, style, props, ctx)`` as an Element."""
    render_fn = func
    el_kind = kind
    el_props = props_model

    class RegisteredElement(Element):
        kind = el_kind
        props_model = el_props

        def render(
            self,
            slide: Slide,
            box: Box,
            style: ElementStyle,
            props: BaseModel,
            ctx: RenderContext,
        ) -> None:
            render_fn(slide, box, style, props, ctx)

    return RegisteredElement()


def apply_box_padding(box: Box, style: ElementStyle) -> Box:
    """Shrink an EMU box by the element's padding fractions."""
    left, top, width, height = box
    pad_x = int(style.pad_x * width)
    pad_y = int(style.pad_y * height)
    return (left + pad_x, top + pad_y, max(1, width - 2 * pad_x), max(1, height - 2 * pad_y))


def vertical_anchor(style: ElementStyle) -> MSO_ANCHOR:
    """Return the MSO vertical anchor for the element's valign."""
    return _ANCHOR_MAP.get(style.valign or "start", MSO_ANCHOR.TOP)


def style_paragraph(
    paragraph,
    ctx: RenderContext,
    *,
    size_pt: float | None,
    bold: bool | None,
    color_token: str | None,
    align: str | None,
) -> None:
    """Apply size, weight, color, and alignment to one paragraph's runs."""
    if align is not None and align in _ALIGN_MAP:
        paragraph.alignment = _ALIGN_MAP[align]
    color_hex = (
        theme.resolve_color_token(color_token, ctx.palette)
        if color_token is not None
        else None
    )
    for run in paragraph.runs:
        if size_pt is not None:
            run.font.size = Pt(size_pt)
        if bold is not None:
            run.font.bold = bold
        if color_hex is not None:
            from slides_factory.brand import hex_to_rgb

            run.font.color.rgb = hex_to_rgb(color_hex)
