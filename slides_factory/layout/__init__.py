"""Layout helpers — percent boxes, RTL mirroring, fonts, and font embedding."""

from slides_factory.layout.font_embed import embed_fonts_in_pptx
from slides_factory.layout.fonts import apply_paragraph_font, apply_shape_font, font_family_from_file
from slides_factory.layout.pct import (
    LOGO_WIDTH_CM,
    LOGO_WIDTH_PRESENTATION_TITLE_CM,
    LogoPlacement,
    PctBox,
    image_aspect_ratio,
    resolve_logo_placement,
)
from slides_factory.layout.rtl import RTLLayout

__all__ = [
    "LOGO_WIDTH_CM",
    "LOGO_WIDTH_PRESENTATION_TITLE_CM",
    "LogoPlacement",
    "PctBox",
    "RTLLayout",
    "apply_paragraph_font",
    "apply_shape_font",
    "embed_fonts_in_pptx",
    "font_family_from_file",
    "image_aspect_ratio",
    "resolve_logo_placement",
]
