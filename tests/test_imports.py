"""Verify every public module can be imported independently without side effects."""

import importlib

import pytest

PUBLIC_MODULES = [
    "slides_factory",
    "slides_factory.app",
    "slides_factory.document",
    "slides_factory.template",
    "slides_factory.frame",
    "slides_factory.palette",
    "slides_factory.render_context",
    "slides_factory.layout_spec",
    "slides_factory.models",
    "slides_factory.typing_utils",
    "slides_factory.templating",
    "slides_factory.template_input",
    "slides_factory.frame_info",
    "slides_factory.locale",
    "slides_factory.metadata",
    "slides_factory.registration",
    "slides_factory.layout.grid",
    "slides_factory.layout.render",
    "slides_factory.layout.pct",
    "slides_factory.layout.fonts",
    "slides_factory.layout.font_embed",
    "slides_factory.layout.locks",
    "slides_factory.layout.rtl",
    "slides_factory.layout.z_order",
    "slides_factory.elements.base",
    "slides_factory.elements.card",
    "slides_factory.elements.text",
    "slides_factory.styling.theme",
    "slides_factory.styling.tokens",
    "slides_factory.styling.models",
    "slides_factory.brand.theme",
    "slides_factory.brand.doc",
    "slides_factory.brand.logos",
    "slides_factory.core.engine",
    "slides_factory.core.manager",
    "slides_factory.core.session",
    "slides_factory.core.grid",
]


@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_module_imports_cleanly(module_name):
    """Each public module should import without errors."""
    importlib.import_module(module_name)
