"""Slide palette abstraction — colors frames pass to templates via RenderContext.

Functions:
    apply_paragraph_color      — Set font color on every run in a paragraph.
    apply_shape_palette_text   — Apply palette text color to all paragraphs in a shape.

Classes:
    SlidePalette — text, highlight, main, and extras pool for one frame look.
"""

from __future__ import annotations

from dataclasses import dataclass

from slides_factory.brand import hex_to_rgb


@dataclass(frozen=True)
class SlidePalette:
    """Colors a frame passes to content templates for one background look."""

    text: str
    highlight: str
    main: tuple[str, ...]
    extras: tuple[str, ...]
    extras_start: int = 0
    extras_end: int | None = None

    def usable_extras(self) -> tuple[str, ...]:
        """Return the extras slice templates may pick from."""
        end = self.extras_end if self.extras_end is not None else len(self.extras)
        return self.extras[self.extras_start:end]

    def extra_at(self, index: int) -> str:
        """Pick a color from usable extras, wrapping when index exceeds length."""
        pool = self.usable_extras()
        if not pool:
            raise ValueError("palette has no usable extras")
        return pool[index % len(pool)]


def apply_paragraph_color(paragraph, hex_color: str) -> None:
    """Set font color on every run in one paragraph."""
    rgb = hex_to_rgb(hex_color)
    for run in paragraph.runs:
        run.font.color.rgb = rgb


def apply_shape_palette_text(shape, palette: SlidePalette) -> None:
    """Apply palette text color to all paragraphs in a shape's text frame."""
    if not shape.has_text_frame:
        return
    for paragraph in shape.text_frame.paragraphs:
        apply_paragraph_color(paragraph, palette.text)
