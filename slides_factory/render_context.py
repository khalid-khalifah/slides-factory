"""Per-slide render settings passed into every template.

Classes:
    RenderContext — Immutable snapshot of rtl, locale, slide_width for one render call.

Methods:
    from_presentation — Build context from a Presentation plus rtl/locale flags.
    with_palette        — Return a copy with the frame palette attached.
    mirror_left         — Core RTL formula: slide_width - left - width, with right-side
                          anchoring for wide/symmetric shapes so Arabic text has room.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from pptx.util import Length

from slides_factory.geometry import Box

if TYPE_CHECKING:
    from slides_factory.brand import BrandTheme
    from slides_factory.palette import SlidePalette


@dataclass(frozen=True)
class RenderContext:
    """Settings every template receives when rendering a slide."""

    rtl: bool = False
    locale: str = "en"
    slide_width: int = 0
    slide_height: int = 0
    font_name: str = "Arial"
    brand: BrandTheme | None = None
    palette: SlidePalette | None = None
    playground: Box | None = None
    debug: bool = False

    def with_palette(self, palette: SlidePalette) -> RenderContext:
        """Return a copy with the frame palette attached for template rendering."""
        return replace(self, palette=palette)

    def with_playground(self, playground: Box) -> RenderContext:
        """Return a copy with the resolved playground region (EMU) attached."""
        return replace(self, playground=playground)

    def with_debug(self, debug: bool = True) -> RenderContext:
        """Return a copy with debug-mode enabled."""
        return replace(self, debug=debug)

    @classmethod
    def from_presentation(
        cls,
        prs,
        *,
        rtl: bool,
        locale: str,
        brand: BrandTheme | None = None,
    ) -> RenderContext:
        """Create render context from presentation dimensions and locale flags."""
        from slides_factory.locale import normalize_locale

        normalized = normalize_locale(locale)
        if rtl and normalized == "en":
            normalized = "ar"
        font_name = brand.fonts.family_for(brand, "body") if brand else "Arial"
        return cls(
            rtl=rtl,
            locale=normalized,
            slide_width=int(prs.slide_width),
            slide_height=int(prs.slide_height),
            font_name=font_name,
            brand=brand,
        )

    def mirror_left(self, left: int | Length, width: int | Length) -> int:
        """Flip horizontal position for RTL: slide_width - left - width.

        Full-width / symmetric shapes are anchored to the right so the left
        margin is larger than the right margin (room for RTL text).
        """
        left_i = int(left)
        width_i = int(width)
        if not self.rtl:
            return left_i

        sw = self.slide_width
        mirrored = sw - left_i - width_i
        margin_left = mirrored
        margin_right = sw - mirrored - width_i

        is_wide = width_i > sw * 0.55
        needs_anchor = mirrored == left_i or (is_wide and margin_left <= margin_right)
        if needs_anchor:
            right_margin = max(left_i // 2, 91440)  # at least ~0.1"
            mirrored = sw - width_i - right_margin

        return max(0, min(mirrored, sw - width_i))
