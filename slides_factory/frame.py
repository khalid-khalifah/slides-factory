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
from typing import ClassVar

from pptx.slide import Slide

from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext


class FrameTemplate(ABC):
    """Page shell applied before content templates fill placeholders."""

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    palette: ClassVar[SlidePalette]

    @abstractmethod
    def render(self, slide: Slide, ctx: RenderContext) -> None:
        """Apply background and other page-level visuals to the slide."""


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
