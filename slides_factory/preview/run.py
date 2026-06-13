"""Launch the Streamlit preview app from the CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_preview(
    *,
    impl_module: str | None,
    brand_path: Path | None = None,
    page_title: str | None = None,
    extra_args: list[str] | None = None,
) -> int:
    """Start Streamlit with the generic preview launcher."""
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Streamlit is not installed. Install preview extras: uv sync --group preview"
        ) from exc

    if not impl_module:
        raise RuntimeError(
            "Preview is not configured for this SlideFactory. "
            "Pass preview_impl_module when creating the app instance."
        )

    from slides_factory.preview.launcher import __file__ as launcher_path

    env = os.environ.copy()
    env["SLIDES_FACTORY_IMPL"] = impl_module
    if brand_path is not None:
        env["SLIDES_FACTORY_PREVIEW_BRAND"] = str(brand_path.resolve())
    if page_title:
        env["SLIDES_FACTORY_PREVIEW_TITLE"] = page_title

    cmd = [sys.executable, "-m", "streamlit", "run", launcher_path, *(extra_args or [])]
    return subprocess.run(cmd, env=env, check=False).returncode
