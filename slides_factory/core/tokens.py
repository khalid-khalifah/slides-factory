from enum import Enum


class ThemeToken(Enum):
    """
    Semantic tokens that represent a visual role rather than a specific color.
    The actual value is resolved based on the active brand and profile.
    """

    # Brand Identity
    BRAND_PRIMARY = "brand.primary"
    BRAND_SECONDARY = "brand.secondary"

    # Text Roles
    TEXT_MAIN = "text.main"
    TEXT_MUTED = "text.muted"
    TEXT_INVERTED = "text.inverted"  # High contrast for dark backgrounds

    # Surface/Background Roles
    SURFACE_BG = "surface.bg"
    SURFACE_CONTRAST = "surface.contrast"

    # Functional Roles
    ACCENT_HIGHLIGHT = "accent.highlight"
    BORDER_SUBTLE = "border.subtle"

    @classmethod
    def from_string(cls, value: str):
        for token in cls:
            if token.value == value:
                return token
        raise ValueError(f"Unknown theme token: {value}")
