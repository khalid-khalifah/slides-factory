from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from slides_factory.core.tokens import ThemeToken


class ThemeResolver:
    """
    Resolves semantic tokens into actual hex colors based on the active brand
    and the specific contrast profile (e.g., 'light', 'dark').
    """

    def __init__(self, theme_config_path: Path):
        self.config = self._load_config(theme_config_path)
        self._global_colors = self.config.get("colors", {})
        self._profiles = self.config.get("profiles", {})

    def _load_config(self, path: Path) -> Dict[str, Any]:
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def resolve(self, token: ThemeToken, profile_name: str) -> str:
        """
        Resolves a token based on the provided profile name.
        Example: resolve(ThemeToken.TEXT_MAIN, "dark_mode")
        """
        profile = self._profiles.get(profile_name)
        if not profile:
            # Fallback to 'default' profile or raise error
            profile = self._profiles.get("default", {})
            if not profile:
                return "#000000"  # Absolute fallback

        value = profile.get(token.value)
        if not value:
            # If token is missing from profile, try to find it in a global 'tokens' section
            value = self.config.get("tokens", {}).get(token.value, "#000000")

        # Handle references like "colors.purple_dark"
        if isinstance(value, str) and value.startswith("colors."):
            color_key = value.split(".")[1]
            return self._global_colors.get(color_key, value)

        return value
