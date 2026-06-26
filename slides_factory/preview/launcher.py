"""Generic Streamlit entry — imports the implementation module, then starts the preview UI."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

from slides_factory.preview.app import run_preview_app  # noqa: E402

impl_module = os.environ.get("SLIDES_FACTORY_IMPL")
if impl_module:
    impl = importlib.import_module(impl_module)
else:
    raise RuntimeError("SLIDES_FACTORY_IMPL environment variable not set")

brand_raw = os.environ.get("SLIDES_FACTORY_PREVIEW_BRAND")
page_title = os.environ.get("SLIDES_FACTORY_PREVIEW_TITLE")

run_preview_app(
    impl.app,  # type: ignore[union-attr]
    brand_path=Path(brand_raw) if brand_raw else None,
    page_title=page_title,
)
