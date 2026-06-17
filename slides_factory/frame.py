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
from typing import Any, ClassVar

from pptx.slide import Slide

from slides_factory.frame_info import FrameInfo
from slides_factory.layout.pct import PctBox, resolve_pct_box
from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext

# Body region used when a frame does not declare its own playground, and when a
# slide has no brand/frame at all. Leaves side margins and a title band on top.
DEFAULT_PLAYGROUND = PctBox(left=6, top=20, width=88, height=72)


class FrameTemplate(ABC):
    """Page shell applied before content templates fill placeholders.

    A frame paints chrome (background, fixed shapes), draws an information layer
    from :class:`FrameInfo` (title, page number), and may declare a
    ``playground`` region where layout content is placed.
    """

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    palette: ClassVar[SlidePalette]
    playground: ClassVar[PctBox | None] = None
    frame_info_model: ClassVar[type[FrameInfo]] = FrameInfo
    allows_layout: ClassVar[bool] = True

    @classmethod
    def validate_info(cls, data: dict[str, Any]) -> FrameInfo:
        """Validate raw JSON against this frame's ``frame_info_model``."""
        return cls.frame_info_model.model_validate(data)

    @classmethod
    def get_info_json_schema(cls) -> dict[str, Any]:
        """Return the JSON Schema for this frame's info model."""
        return cls.frame_info_model.model_json_schema()

    def playground_box(self, ctx: RenderContext) -> tuple[int, int, int, int]:
        """Resolve the frame's body region to an EMU ``(left, top, width, height)``."""
        if not self.allows_layout:
            raise ValueError(
                f"Frame {self.id!r} does not allow layout content (no playground)."
            )
        box = self.playground if self.playground is not None else DEFAULT_PLAYGROUND
        return resolve_pct_box(ctx, box)

    @abstractmethod
    def render(self, slide: Slide, ctx: RenderContext, info: FrameInfo | None = None) -> None:
        """Apply background, fixed shapes, and the information layer to the slide."""


def list_frames() -> list[FrameTemplate]:
    """Return instances of every registered frame."""
    from slides_factory.app import get_app

    return get_app().list_frames()


def get_frame(frame_id: str) -> FrameTemplate:
    """Return a frame instance by id, or raise KeyError."""
    from slides_factory.app import get_app

    return get_app().get_frame(frame_id)


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
