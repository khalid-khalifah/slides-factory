"""Frame template protocol.

Classes:
    FrameTemplate — Abstract base for frame implementations (render only).

Functions:
    list_frames      — Return instances of every registered frame.
    get_frame        — Return a frame instance by id, or raise KeyError.
    resolve_frame_id — Resolve frame: CLI > stored > template default > brand default > fallback.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.frame_info import EmptyFrameInput
from slides_factory.geometry import Box
from slides_factory.layout.pct import PctBox, resolve_pct_box
from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext
from slides_factory.styling.models import EmptyStyle

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory

# Body region used when a frame does not declare its own playground, and when a
# slide has no brand/frame at all. Leaves side margins and a title band on top.
DEFAULT_PLAYGROUND = PctBox(left=6, top=20, width=88, height=72)


class FrameTemplate(ABC):
    """Page shell applied before content templates fill placeholders.

    A frame paints chrome (background, fixed shapes), draws an information layer
    from its ``frame_input``, and may declare a ``playground`` region where
    layout content is placed.
    """

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    palette: ClassVar[SlidePalette]
    playground: ClassVar[PctBox | None] = None
    frame_input: ClassVar[type[BaseModel]] = EmptyFrameInput
    frame_style: ClassVar[type[BaseModel]] = EmptyStyle
    allows_layout: ClassVar[bool] = True

    @classmethod
    def palette_for(
        cls,
        ctx: RenderContext,
        frame_style: BaseModel | None = None,
    ) -> SlidePalette:
        """Return the palette for this frame, deriving from brand when possible."""
        if ctx.brand is None:
            return cls.palette
        style = frame_style if frame_style is not None else cls.frame_style()
        if hasattr(style, "background_group") and hasattr(style, "background_index"):
            from slides_factory.palette import palette_from_brand_surface

            return palette_from_brand_surface(
                ctx.brand,
                group=style.background_group,
                index=style.background_index,
                highlight_group="main",
                highlight_index=0,
            )
        return cls.palette

    @classmethod
    def validate_info(cls, data: dict[str, Any]) -> BaseModel:
        """Validate raw JSON against this frame's ``frame_input``."""
        return cls.frame_input.model_validate(data)

    @classmethod
    def validate_style(cls, data: dict[str, Any] | None) -> BaseModel:
        """Validate raw JSON against this frame's ``frame_style``."""
        return cls.frame_style.model_validate(data or {})

    @classmethod
    def get_info_json_schema(cls) -> dict[str, Any]:
        """Return the JSON Schema for this frame's input model."""
        return cls.frame_input.model_json_schema()

    @classmethod
    def get_style_json_schema(cls) -> dict[str, Any]:
        """Return the JSON Schema for this frame's style model."""
        return cls.frame_style.model_json_schema()

    def playground_box(self, ctx: RenderContext) -> Box:
        """Resolve the frame's body region as a :class:`Box` (EMU)."""
        if not self.allows_layout:
            raise ValueError(f"Frame {self.id!r} does not allow layout content (no playground).")
        box = self.playground if self.playground is not None else DEFAULT_PLAYGROUND
        return resolve_pct_box(ctx, box)

    @abstractmethod
    def render(
        self,
        slide: Slide,
        ctx: RenderContext,
        info: BaseModel | None = None,
        style: BaseModel | None = None,
    ) -> None:
        """Apply background, fixed shapes, and the information layer to the slide."""


def list_frames(app: SlideFactory) -> list[FrameTemplate]:
    """Return instances of every registered frame."""
    return app.list_frames()


def get_frame(app: SlideFactory, frame_id: str) -> FrameTemplate:
    """Return a frame instance by id, or raise KeyError."""
    return app.get_frame(frame_id)


def resolve_frame_id(
    *,
    frame: str | None,
    stored: str | None = None,
    template_default: str | None = None,
    brand_default: str | None = None,
    fallback: str = "basic",
) -> str:
    """Resolve frame: CLI override > stored > template default > brand default > fallback."""
    if frame:
        return frame
    if stored:
        return stored
    if template_default:
        return template_default
    if brand_default:
        return brand_default
    return fallback
