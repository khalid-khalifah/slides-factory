"""Brand theme loading, document persistence, and logo assets."""

from slides_factory.brand.theme import (
    BrandColor,
    BrandColors,
    BrandFonts,
    BrandFontSpec,
    BrandLayout,
    BrandTheme,
    ColorGroup,
    PageSpec,
    load_brand,
    resolve_color,
    resolve_contrast,
)
from slides_factory.color_utils import hex_to_rgb

__all__ = [
    "BrandColor",
    "BrandColors",
    "BrandFontSpec",
    "BrandFonts",
    "BrandLayout",
    "BrandTheme",
    "ColorGroup",
    "PageSpec",
    "hex_to_rgb",
    "load_brand",
    "resolve_color",
    "resolve_contrast",
]
