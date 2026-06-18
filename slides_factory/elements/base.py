"""Element protocol, registration wrapper, and shared rendering helpers.

Classes:
    Element — Internal protocol: a ``kind``, a Pydantic ``props_model``, and render.

Functions:
    element_from_function — Wrap a render function as an Element instance.
    style_paragraph       — Apply size/bold/color/alignment to one paragraph.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel
from pptx.enum.text import PP_ALIGN
from pptx.slide import Slide

from slides_factory.render_context import RenderContext
from slides_factory.styling import theme

Box = tuple[int, int, int, int]

_ALIGN_MAP = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}


class Element(ABC):
    """Internal protocol every drawable element implements."""

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
        props: BaseModel,
        ctx: RenderContext,
    ) -> None:
        """Draw the element into ``box`` (EMU)."""


def element_from_function(
    func: Callable[..., Any],
    *,
    kind: str,
    props_model: type[BaseModel],
) -> Element:
    """Wrap a render function ``(slide, box, props, ctx)`` as an Element."""
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
            props: BaseModel,
            ctx: RenderContext,
        ) -> None:
            render_fn(slide, box, props, ctx)

    return RegisteredElement()


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
            from pptx.util import Pt

            run.font.size = Pt(size_pt)
        if bold is not None:
            run.font.bold = bold
        if color_hex is not None:
            from slides_factory.brand import hex_to_rgb

            run.font.color.rgb = hex_to_rgb(color_hex)
