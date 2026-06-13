"""Generic Streamlit entry — imports the implementation module, then starts the preview UI."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

impl_module = os.environ.get("SLIDES_FACTORY_IMPL")
if impl_module:
    importlib.import_module(impl_module)

from slides_factory.app import get_app
from slides_factory.preview.app import run_preview_app

brand_raw = os.environ.get("SLIDES_FACTORY_PREVIEW_BRAND")
page_title = os.environ.get("SLIDES_FACTORY_PREVIEW_TITLE")

run_preview_app(
    get_app(),
    brand_path=Path(brand_raw) if brand_raw else None,
    page_title=page_title,
)
