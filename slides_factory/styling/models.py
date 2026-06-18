"""Typed style models for elements and frames (separate from content props)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from slides_factory.brand.theme import BrandTheme, ColorGroup

ColorGroupName = Literal["main", "secondary", "basic"]


class EmptyStyle(BaseModel):
    """Default when a kind does not declare style fields."""


class TextStyle(BaseModel):
    """Look overrides for the text element."""

    font: str = Field(default="body", description="Brand font registry key.")
    text_size: str = Field(default="lg", description="Theme font-size token.")
    text_color: str = Field(
        default="primary",
        description="Palette token, brand fill (main:0), or contrast (on-main:0).",
    )
    bold: bool = False
    align: str = Field(default="left", description="left, center, right, or justify.")


class CardStyle(BaseModel):
    """Look overrides for the card element."""

    font: str = Field(default="body", description="Brand font registry key.")
    background_color: str = Field(
        default="surface",
        description="Palette token or brand fill reference (e.g. main:0).",
    )
    radius: str = Field(default="md", description="Theme radius token.")
    title_size: str = Field(default="sm", description="Theme font-size token.")
    value_size: str = Field(default="2xl", description="Theme font-size token.")
    body_size: str = Field(default="base", description="Theme font-size token.")
    title_color: str = Field(
        default="muted",
        description="Palette token, brand fill, or contrast (on-main:0).",
    )
    value_color: str = Field(
        default="primary",
        description="Palette token, brand fill, or contrast (on-main:0).",
    )
    body_color: str = Field(
        default="primary",
        description="Palette token, brand fill, or contrast (on-main:0).",
    )
    value_bold: bool = True


def resolve_brand_color(brand: BrandTheme, ref: str) -> str:
    """Resolve a brand fill reference like ``main:1`` or ``secondary:0``."""
    pair = _parse_brand_ref(brand, ref)
    return pair.color


def resolve_brand_contrast_ref(brand: BrandTheme, ref: str) -> str:
    """Resolve a brand contrast reference like ``on-main:1``."""
    if not ref.startswith("on-"):
        raise ValueError(f"brand contrast reference must start with 'on-', got {ref!r}")
    pair = _parse_brand_ref(brand, ref.removeprefix("on-"))
    return pair.contrast


def _parse_brand_ref(brand: BrandTheme, ref: str):
    if ":" not in ref:
        raise ValueError(f"brand color reference must be group:index, got {ref!r}")
    group, index_text = ref.split(":", 1)
    if group not in ("main", "secondary", "basic"):
        raise ValueError(f"unknown color group {group!r} in {ref!r}")
    return brand.colors.get(group, int(index_text))  # type: ignore[arg-type]


def is_brand_fill_ref(ref: str) -> bool:
    """True when ``ref`` looks like a brand fill reference (main:0, etc.)."""
    if ":" not in ref:
        return False
    group, index_text = ref.split(":", 1)
    return group in ("main", "secondary", "basic") and index_text.isdigit()

