"""Central theme scale for the styling engine (the "tailwind.config" analog).

Scales are intentionally small and brand-agnostic. Spacing values are
fractions of the relevant region dimension; font sizes are points; radius
values are python-pptx rounded-rectangle adjustment fractions. Color tokens
map to ``SlidePalette`` slots, with neutral fallbacks when no palette exists.

Functions:
    spacing       — Resolve a spacing token (e.g. "4") to a fraction.
    font_size_pt  — Resolve a font-size token (e.g. "lg") to points.
    radius        — Resolve a radius token (e.g. "md") to an adjustment fraction.
    resolve_color_token — Resolve a color token to a #RRGGBB string.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slides_factory.palette import SlidePalette

# Spacing scale: token -> fraction of the region dimension it applies to.
SPACING_SCALE: dict[int, float] = {
    0: 0.0,
    1: 0.0125,
    2: 0.025,
    3: 0.0375,
    4: 0.05,
    5: 0.0625,
    6: 0.075,
    8: 0.10,
    10: 0.125,
    12: 0.15,
    16: 0.20,
}

# Font-size scale: token -> points.
FONT_SIZES_PT: dict[str, float] = {
    "xs": 10.0,
    "sm": 12.0,
    "base": 14.0,
    "lg": 18.0,
    "xl": 24.0,
    "2xl": 32.0,
    "3xl": 40.0,
    "4xl": 54.0,
}

# Font-weight tokens -> bold flag.
FONT_WEIGHTS: dict[str, bool] = {
    "normal": False,
    "medium": False,
    "semibold": True,
    "bold": True,
}

# Radius scale: token -> rounded-rectangle adjustment fraction (0..0.5).
RADIUS_SCALE: dict[str, float] = {
    "none": 0.0,
    "sm": 0.05,
    "md": 0.10,
    "lg": 0.16,
    "xl": 0.24,
    "full": 0.5,
}

# Horizontal/vertical alignment tokens.
TEXT_ALIGNS: frozenset[str] = frozenset({"left", "center", "right", "justify"})

# Neutral fallbacks when no palette is attached (no brand/frame).
_FALLBACK_COLORS: dict[str, str] = {
    "primary": "#111111",
    "highlight": "#2563EB",
    "main": "#F3F4F6",
    "surface": "#F3F4F6",
    "muted": "#6B7280",
}

COLOR_TOKENS: frozenset[str] = frozenset(_FALLBACK_COLORS)


def spacing(token: int) -> float:
    """Return the fraction for a spacing token, raising on unknown values."""
    if token not in SPACING_SCALE:
        allowed = ", ".join(str(k) for k in sorted(SPACING_SCALE))
        raise ValueError(f"unknown spacing step {token!r}; allowed: {allowed}")
    return SPACING_SCALE[token]


def font_size_pt(token: str) -> float:
    """Return the point size for a font-size token, raising on unknown values."""
    if token not in FONT_SIZES_PT:
        allowed = ", ".join(sorted(FONT_SIZES_PT))
        raise ValueError(f"unknown font size {token!r}; allowed: {allowed}")
    return FONT_SIZES_PT[token]


def radius(token: str) -> float:
    """Return the adjustment fraction for a radius token, raising on unknown values."""
    if token not in RADIUS_SCALE:
        allowed = ", ".join(sorted(RADIUS_SCALE))
        raise ValueError(f"unknown radius {token!r}; allowed: {allowed}")
    return RADIUS_SCALE[token]


def resolve_color_token(token: str, palette: SlidePalette | None) -> str:
    """Resolve a color token to a ``#RRGGBB`` string against a palette.

    Tokens bind to palette slots so decks stay on-brand; without a palette the
    neutral fallbacks keep the grid renderable.
    """
    if token not in _FALLBACK_COLORS:
        allowed = ", ".join(sorted(_FALLBACK_COLORS))
        raise ValueError(f"unknown color token {token!r}; allowed: {allowed}")
    if palette is None:
        return _FALLBACK_COLORS[token]
    if token == "primary":
        return palette.text
    if token == "highlight":
        return palette.highlight
    if token in ("main", "surface"):
        return palette.main[0]
    if token == "muted":
        extras = palette.usable_extras()
        if extras:
            return extras[0]
        return palette.main[0]
    return _FALLBACK_COLORS[token]  # pragma: no cover - exhaustive above
