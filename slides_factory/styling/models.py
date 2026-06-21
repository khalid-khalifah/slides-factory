"""Typed style models for elements and frames (separate from content props).

Brand color reference helpers are re-exported from ``brand.theme`` where they
logically belong — they operate on ``BrandTheme`` rather than styling concepts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Re-export brand color resolution helpers from their canonical location.
from slides_factory.brand.theme import (
    is_brand_contrast_ref,  # noqa: F401
    is_brand_fill_ref,  # noqa: F401
    resolve_brand_color,  # noqa: F401
    resolve_brand_contrast_ref,  # noqa: F401
)

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
