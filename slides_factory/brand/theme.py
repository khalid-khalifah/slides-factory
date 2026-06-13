"""Brand theme loaded from YAML (colors, fonts, logos, page size, layout).

Functions:
    _parse_logos   — Parse nested ``{variant: {en, ar}}`` logos into flat runtime keys.
    _parse_layout  — Parse raw layout dict into BrandLayout.
    load_brand     — Load and validate brand theme from a YAML file.
    resolve_color  — Shorthand for brand.colors.get(group, index).
    hex_to_rgb     — Parse a ``#RRGGBB`` string into a python-pptx RGBColor.

Classes:
    BrandColors    — Brand palette as three ordered lists (main, secondary, basic).
    BrandFontSpec  — Font slot with optional file path and resolved family name.
    BrandFonts     — Title, body, and footer font slots.
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


class BrandColors(BaseModel):
    """Brand palette as three ordered lists (index 0 is the primary swatch per group)."""

    main: list[str] = Field(min_length=1)
    secondary: list[str] = Field(default_factory=list)
    basic: list[str] = Field(default_factory=list)

    @field_validator("main", "secondary", "basic", mode="before")
    @classmethod
    def _normalize_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("expected a list of color strings")
        return [cls._normalize_hex(item) for item in value]

    @staticmethod
    def _normalize_hex(value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("color must be a string")
        text = value.strip()
        if not _HEX_RE.match(text):
            raise ValueError(f"invalid hex color: {value!r}")
        return text if text.startswith("#") else f"#{text.upper()}"

    def get(self, group: ColorGroup, index: int) -> str:
        """Return a color from the given group and zero-based index."""
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


class BrandFonts(BaseModel):
    """Named font slots referenced by content and frame templates."""

    title: BrandFontSpec = Field(default_factory=lambda: BrandFontSpec(family="Arial"))
    body: BrandFontSpec = Field(default_factory=lambda: BrandFontSpec(family="Arial"))
    footer: BrandFontSpec | None = None

    @field_validator("title", "body", "footer", mode="before")
    @classmethod
    def _coerce_slot(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return {"family": value}
        return value

    def family_for(self, brand: BrandTheme, slot: Literal["title", "body", "footer"]) -> str:
        if slot == "title":
            return self.title.resolve_family(brand)
        if slot == "footer" and self.footer is not None:
            return self.footer.resolve_family(brand)
        return self.body.resolve_family(brand)

    def embeddable_fonts(self, brand: BrandTheme) -> list[tuple[str, Path]]:
        seen: set[Path] = set()
        fonts: list[tuple[str, Path]] = []
        for spec in (self.title, self.body, self.footer):
            if spec is None:
                continue
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
        fonts=BrandFonts.model_validate(raw.get("fonts") or {}),
        logos=logos,
        source_path=source,
    )
    return theme


def resolve_color(brand: BrandTheme, group: ColorGroup, index: int) -> str:
    """Shorthand for brand.colors.get(group, index)."""
    return brand.colors.get(group, index)


def hex_to_rgb(hex_color: str) -> RGBColor:
    """Parse a ``#RRGGBB`` string into a python-pptx RGBColor."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"invalid hex color: {hex_color!r}")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
