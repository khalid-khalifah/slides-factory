"""Slide palette abstraction — colors frames pass to templates via RenderContext.

Functions:
    apply_paragraph_color      — Set font color on every run in a paragraph.
    apply_shape_palette_text   — Apply palette text color to all paragraphs in a shape.

Classes:
    SlidePalette — text, highlight, main, and extras pool for one frame look.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from slides_factory.brand import hex_to_rgb

if TYPE_CHECKING:
    from slides_factory.brand.theme import BrandTheme, ColorGroup


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


def palette_from_brand_surface(
    brand: BrandTheme,
    *,
    group: ColorGroup,
    index: int,
    highlight_group: ColorGroup = "secondary",
    highlight_index: int = 0,
) -> SlidePalette:
    """Build a ``SlidePalette`` from one brand surface pair and highlight swatch."""
    surface = brand.colors.get(group, index)
    highlight = brand.colors.get(highlight_group, highlight_index)

    main_colors: list[str] = [surface.color]
    for pair in brand.colors.secondary:
        if pair.color not in main_colors:
            main_colors.append(pair.color)
    for pair in brand.colors.main:
        if pair.color not in main_colors:
            main_colors.append(pair.color)

    extras: list[str] = []
    for pool_group in ("secondary", "basic"):
        for pair in getattr(brand.colors, pool_group):
            for hex_color in (pair.color, pair.contrast):
                if hex_color != surface.color and hex_color not in extras:
                    extras.append(hex_color)

    return SlidePalette(
        text=surface.contrast,
        highlight=highlight.color,
        main=tuple(main_colors),
        extras=tuple(extras) if extras else (surface.contrast,),
    )
