"""Brand theme loading, document persistence, and logo assets."""

from slides_factory.brand.doc import get_document_brand_path, set_document_brand
from slides_factory.brand.logos import (
    locale_logo_base,
    place_header_logo,
    rasterize_svg,
    resolve_flat_logo_key,
    resolve_logo_key,
    resolve_raster_logo,
)
from slides_factory.brand.theme import (
    BrandColors,
    BrandFontSpec,
    BrandFonts,
    BrandLayout,
    BrandTheme,
    ColorGroup,
    PageSpec,
    hex_to_rgb,
    load_brand,
    resolve_color,
)

__all__ = [
    "BrandColors",
    "BrandFontSpec",
    "BrandFonts",
    "BrandLayout",
    "BrandTheme",
    "ColorGroup",
    "PageSpec",
    "get_document_brand_path",
    "hex_to_rgb",
    "load_brand",
    "locale_logo_base",
    "place_header_logo",
    "rasterize_svg",
    "resolve_color",
    "resolve_flat_logo_key",
    "resolve_logo_key",
    "resolve_raster_logo",
    "set_document_brand",
]
