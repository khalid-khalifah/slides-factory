from pathlib import Path

import pytest
import yaml

from slides_factory.core.resolver import ThemeResolver
from slides_factory.core.tokens import ThemeToken


@pytest.fixture
def theme_config(tmp_path: Path):
    config = {
        "colors": {
            "purple_dark": "#413258",
            "cyan_bright": "#1AD9C7",
            "white": "#FFFFFF",
            "grey_darkest": "#1A1A1A",
        },
        "profiles": {
            "light_mode": {
                "surface.bg": "colors.white",
                "text.main": "colors.grey_darkest",
                "accent.highlight": "colors.purple_dark",
            },
            "dark_mode": {
                "surface.bg": "colors.purple_dark",
                "text.main": "colors.white",
                "accent.highlight": "colors.cyan_bright",
            },
            "default": {
                "surface.bg": "#FFFFFF",
                "text.main": "#000000",
            },
        },
    }
    path = tmp_path / "theme.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f)
    return path


def test_resolve_basic(theme_config):
    resolver = ThemeResolver(theme_config)
    # Light mode -> white background
    assert resolver.resolve(ThemeToken.SURFACE_BG, "light_mode") == "#FFFFFF"
    # Dark mode -> purple background
    assert resolver.resolve(ThemeToken.SURFACE_BG, "dark_mode") == "#413258"


def test_resolve_contrast_shift(theme_config):
    resolver = ThemeResolver(theme_config)
    # Light mode text is dark grey
    assert resolver.resolve(ThemeToken.TEXT_MAIN, "light_mode") == "#1A1A1A"
    # Dark mode text is white (Contrast safety!)
    assert resolver.resolve(ThemeToken.TEXT_MAIN, "dark_mode") == "#FFFFFF"


def test_fallback_to_default_profile(theme_config):
    resolver = ThemeResolver(theme_config)
    # Non-existent profile should use default
    assert resolver.resolve(ThemeToken.SURFACE_BG, "ghost_mode") == "#FFFFFF"


def test_absolute_fallback(tmp_path: Path):
    # Empty config
    path = tmp_path / "empty.yaml"
    path.write_text("colors: {}\nprofiles: {}")
    resolver = ThemeResolver(path)
    assert resolver.resolve(ThemeToken.TEXT_MAIN, "any") == "#000000"
