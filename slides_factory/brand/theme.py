"""Brand theme loaded from YAML (colors, fonts, logos, page size, layout).

Functions:
    _parse_logos   — Parse nested ``{variant: {en, ar}}`` logos into flat runtime keys.
    _parse_layout  — Parse raw layout dict into BrandLayout.
    load_brand     — Load and validate brand theme from a YAML file.
    resolve_color    — Shorthand for brand.colors.get(group, index).color.
    resolve_contrast — Shorthand for brand.colors.get(group, index).contrast.
    hex_to_rgb     — Parse a ``#RRGGBB`` string into a python-pptx RGBColor.

Classes:
    BrandColor     — Fill color and contrast hex pair.
    BrandColors    — Brand palette as three ordered lists of BrandColor pairs.
    BrandFontSpec  — Font slot with optional file path and resolved family name.
    BrandFonts     — Font registry keyed by YAML names (title, body, footer, …).
    PageSpec       — Slide width and height in inches.
    BrandLayout    — Percent-based logo anchors and named element boxes.
    BrandTheme     — Full theme: colors, fonts, logos, page size, and layout.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches

from slides_factory.layout.pct import LogoPlacement, PctBox

ColorGroup = Literal["main", "secondary", "basic"]

_HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


class BrandColor(BaseModel):
    """One brand swatch: fill color and readable contrast on that fill."""

    color: str
    contrast: str

    @field_validator("color", "contrast", mode="before")
    @classmethod
    def _normalize_hex(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("color and contrast must be hex strings")
        text = value.strip()
        if not _HEX_RE.match(text):
            raise ValueError(f"invalid hex color: {value!r}")
        return text if text.startswith("#") else f"#{text.upper()}"


def _coerce_color_entry(value: object) -> BrandColor:
    if isinstance(value, str):
        raise ValueError(
            "brand colors must be mappings with 'color' and 'contrast' keys; "
            f"got plain string {value!r}"
        )
    if isinstance(value, dict):
        return BrandColor.model_validate(value)
    raise TypeError(
        f"brand color entry must be a mapping with color and contrast, got {type(value).__name__}"
    )


class BrandColors(BaseModel):
    """Brand palette as three ordered lists of color + contrast pairs."""

    main: list[BrandColor] = Field(min_length=1)
    secondary: list[BrandColor] = Field(default_factory=list)
    basic: list[BrandColor] = Field(default_factory=list)

    @field_validator("main", "secondary", "basic", mode="before")
    @classmethod
    def _normalize_list(cls, value: object) -> list[BrandColor]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("expected a list of color mappings")
        return [_coerce_color_entry(item) for item in value]

    def get(self, group: ColorGroup, index: int) -> BrandColor:
        """Return a color pair from the given group and zero-based index."""
        items = getattr(self, group)
        if index < 0 or index >= len(items):
            raise IndexError(
                f"colors.{group}[{index}] out of range (0-{len(items) - 1})"
            )
        return items[index]


class BrandFontSpec(BaseModel):
    """One theme font slot — family name and/or path to a TTF/OTF in assets."""

    family: str | None = None
    file: Path | None = None

    def resolve_family(self, brand: BrandTheme) -> str:
        if self.family:
            return self.family
        if self.file is not None and brand.source_path is not None:
            from slides_factory.layout.fonts import font_family_from_file

            path = brand.resolve_path(self.file)
            if path.is_file():
                return font_family_from_file(path)
        return self.family or "Arial"

    def resolve_file(self, brand: BrandTheme) -> Path | None:
        if self.file is None or brand.source_path is None:
            return None
        path = brand.resolve_path(self.file)
        return path if path.is_file() else None


_FONT_EXTENSIONS = frozenset({".ttf", ".otf", ".woff", ".woff2"})


def _looks_like_font_path(text: str) -> bool:
    lowered = text.lower()
    return (
        "/" in text
        or "\\" in text
        or any(lowered.endswith(ext) for ext in _FONT_EXTENSIONS)
    )


def _coerce_font_entry(value: object) -> BrandFontSpec:
    if value is None:
        return BrandFontSpec(family="Arial")
    if isinstance(value, str):
        text = value.strip()
        if _looks_like_font_path(text):
            return BrandFontSpec(file=Path(text))
        return BrandFontSpec(family=text)
    if isinstance(value, dict):
        return BrandFontSpec.model_validate(value)
    raise TypeError(f"font entry must be a path, family name, or mapping, got {type(value).__name__}")


def _parse_fonts(raw: object) -> BrandFonts:
    if not isinstance(raw, dict):
        return BrandFonts()
    slots = {str(key): _coerce_font_entry(value) for key, value in raw.items()}
    return BrandFonts(slots=slots)


class BrandFonts(BaseModel):
    """Named font registry referenced by style fields and render helpers."""

    slots: dict[str, BrandFontSpec] = Field(
        default_factory=lambda: {
            "title": BrandFontSpec(family="Arial"),
            "body": BrandFontSpec(family="Arial"),
        }
    )

    def family_for(self, brand: BrandTheme, key: str) -> str:
        spec = self.slots.get(key) or self.slots.get("body")
        if spec is None:
            return "Arial"
        return spec.resolve_family(brand)

    def embeddable_fonts(self, brand: BrandTheme) -> list[tuple[str, Path]]:
        seen: set[Path] = set()
        fonts: list[tuple[str, Path]] = []
        for spec in self.slots.values():
            path = spec.resolve_file(brand)
            if path is None or path in seen:
                continue
            seen.add(path)
            fonts.append((spec.resolve_family(brand), path))
        return fonts


class PageSpec(BaseModel):
    """Slide dimensions applied when creating a deck from this brand."""

    width_in: float = Field(gt=0, default=10.0)
    height_in: float = Field(gt=0, default=7.5)

    @field_validator("width_in", "height_in", mode="before")
    @classmethod
    def _coerce_inches(cls, value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip().removesuffix("in").strip())
        raise TypeError("expected inches as a number")


class BrandLayout(BaseModel):
    """Percent-based positions and sizes keyed by element name."""

    logos: dict[str, LogoPlacement] = Field(default_factory=dict)
    elements: dict[str, PctBox] = Field(default_factory=dict)


class BrandTheme(BaseModel):
    """Brand configuration file (YAML)."""

    name: str
    default_frame: str
    base_pptx: Path | None = None
    lock_frame_shapes: bool = False
    page: PageSpec = Field(default_factory=PageSpec)
    layout: BrandLayout = Field(default_factory=BrandLayout)
    colors: BrandColors
    fonts: BrandFonts = Field(default_factory=BrandFonts)
    logos: dict[str, Path] = Field(default_factory=dict)

    # Set when loaded from disk; not part of YAML.
    source_path: Path | None = Field(default=None, exclude=True)

    def resolve_path(self, relative: Path | str) -> Path:
        """Resolve a path relative to the brand YAML file location."""
        path = Path(relative)
        if path.is_absolute():
            return path
        if self.source_path is None:
            return path.resolve()
        return (self.source_path.parent / path).resolve()

    def resolve_base_pptx(self) -> Path | None:
        """Return resolved base .pptx path, if configured."""
        if self.base_pptx is None:
            return None
        return self.resolve_path(self.base_pptx)

    def resolve_logo(self, key: str) -> Path | None:
        """Return resolved logo path for a key, or None if missing."""
        rel = self.logos.get(key)
        if rel is None:
            return None
        return self.resolve_path(rel)

    def resolve_logo_raster(self, key: str) -> Path | None:
        """Return a raster image path for Pillow / python-pptx (PNG from SVG if needed)."""
        from slides_factory.brand.logos import resolve_raster_logo

        path = self.resolve_logo(key)
        if path is None:
            return None
        return resolve_raster_logo(path)

    def logo_placement(self, logo_key: str) -> LogoPlacement | None:
        """Return percent layout for the logo locale (``en`` or ``ar`` only)."""
        locale = "ar" if logo_key.startswith("ar") else "en"
        return self.layout.logos.get(locale)

    def apply_page_size(self, prs: Presentation) -> None:
        """Set presentation slide width and height from page spec."""
        prs.slide_width = Inches(self.page.width_in)
        prs.slide_height = Inches(self.page.height_in)


_LOGO_VARIANT_SUFFIX = {
    "wordmark": "",
    "inverted": "_inverted",
    "flat_white": "_flat_white",
    "flat_black": "_flat_black",
}


def _parse_logos(raw: object) -> dict[str, Path]:
    """Parse nested ``{variant: {en, ar}}`` logos into flat runtime keys."""
    if not isinstance(raw, dict):
        return {}
    logos: dict[str, Path] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            if key in _LOGO_VARIANT_SUFFIX:
                suffix = _LOGO_VARIANT_SUFFIX[key]
                for locale, path in value.items():
                    if locale in ("en", "ar") and path is not None:
                        logo_key = locale if not suffix else f"{locale}{suffix}"
                        logos[logo_key] = Path(str(path))
            else:
                for locale, path in value.items():
                    logos[f"{locale}_{key}"] = Path(str(path))
        elif isinstance(value, str):
            logos[str(key)] = Path(value)
    return logos


def _parse_layout(raw: object) -> BrandLayout:
    if not isinstance(raw, dict):
        return BrandLayout()
    logos_raw = raw.get("logos") or {}
    elements_raw = raw.get("elements") or {}
    logos = {
        locale: LogoPlacement.model_validate(logos_raw[locale])
        for locale in ("en", "ar")
        if isinstance(logos_raw.get(locale), dict)
    }
    elements = {
        str(k): PctBox.model_validate(v)
        for k, v in elements_raw.items()
        if isinstance(v, dict)
    }
    return BrandLayout(logos=logos, elements=elements)


def load_brand(path: Path) -> BrandTheme:
    """Load and validate brand theme from a YAML file."""
    source = path.resolve()
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"brand file must be a YAML mapping: {source}")

    logos = _parse_logos(raw.get("logos"))

    base = raw.get("base_pptx")
    theme = BrandTheme(
        name=str(raw.get("name") or source.stem),
        default_frame=str(raw["default_frame"]),
        base_pptx=Path(base) if base else None,
        lock_frame_shapes=bool(raw.get("lock_frame_shapes", False)),
        page=PageSpec.model_validate(raw.get("page") or {}),
        layout=_parse_layout(raw.get("layout")),
        colors=BrandColors.model_validate(raw.get("colors") or {}),
        fonts=_parse_fonts(raw.get("fonts")),
        logos=logos,
        source_path=source,
    )
    return theme


def resolve_color(brand: BrandTheme, group: ColorGroup, index: int) -> str:
    """Return the fill hex for a brand color pair."""
    return brand.colors.get(group, index).color


def resolve_contrast(brand: BrandTheme, group: ColorGroup, index: int) -> str:
    """Return the contrast hex for a brand color pair."""
    return brand.colors.get(group, index).contrast
