"""Tests for preview hot-reload helpers."""

from __future__ import annotations

import importlib
import sys
import textwrap
from pathlib import Path

import pytest

from slides_factory.app import SlideFactory
from slides_factory.preview.reload import (
    changed_files,
    file_mtimes,
    module_name_for_path,
    reload_modules,
    watch_paths_for_preview,
)


@pytest.fixture
def reload_factory(tmp_path: Path) -> SlideFactory:
    pkg = tmp_path / "demo_pkg"
    (pkg / "templates").mkdir(parents=True)
    (pkg / "frames").mkdir(parents=True)
    (pkg / "render").mkdir(parents=True)
    (pkg / "templates" / "helpers").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for sub in ("templates", "frames", "render", "templates/helpers"):
        (pkg / sub / "__init__.py").write_text("", encoding="utf-8")

    sys.path.insert(0, str(tmp_path))
    try:
        (pkg / "templates" / "sample.py").write_text(
            textwrap.dedent(
                """
                from demo_pkg.factory import app
                from slides_factory.template_input import TemplateInput

                class SampleInput(TemplateInput):
                    title: str

                @app.template("sample", name="Sample")
                def sample(slide, ctx, data: SampleInput) -> None:
                    slide.shapes.add_textbox(0, 0, 100, 100).text = data.title
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (pkg / "frames" / "plain.py").write_text(
            textwrap.dedent(
                """
                from demo_pkg.factory import app
                from slides_factory.palette import SlidePalette

                @app.frame("plain", name="Plain", palette=SlidePalette(text="#000", highlight="#111", main=("#ccc",), extras=()))
                def plain(slide, ctx) -> None:
                    pass
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (pkg / "render" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
        (pkg / "factory.py").write_text(
            "from slides_factory.app import SlideFactory\napp = SlideFactory('demo')\n",
            encoding="utf-8",
        )

        import demo_pkg.factory as factory_mod

        importlib.reload(factory_mod)
        factory = factory_mod.app
        yield factory
    finally:
        sys.path.remove(str(tmp_path))
        for name in list(sys.modules):
            if name.startswith("demo_pkg"):
                del sys.modules[name]


def test_watch_paths_include_template_frame_helpers_and_brand(
    reload_factory: SlideFactory,
    tmp_path: Path,
) -> None:
    brand = tmp_path / "brand.yaml"
    brand.write_text("name: x\ndefault_frame: plain\ncolors: {main: ['#000']}\n", encoding="utf-8")
    paths = watch_paths_for_preview(
        reload_factory,
        template_id="sample",
        frame_id="plain",
        brand_path=brand,
    )
    names = {path.name for path in paths}
    assert "sample.py" in names
    assert "plain.py" in names
    assert "helper.py" in names
    assert brand.name in names


def test_changed_files_detects_mtime_update(tmp_path: Path) -> None:
    target = tmp_path / "file.py"
    target.write_text("a = 1\n", encoding="utf-8")
    old = file_mtimes([target])
    target.write_text("a = 2\n", encoding="utf-8")
    assert changed_files(old, [target]) == [target]


def test_module_name_for_path_maps_under_impl_package(reload_factory: SlideFactory) -> None:
    # Trigger lazy discovery before accessing private source dicts.
    _ = reload_factory.impl_base_package
    tpl_path = reload_factory._template_sources["sample"]
    assert module_name_for_path(tpl_path, reload_factory) == "demo_pkg.templates.sample"


def test_reload_modules_reregisters_template(reload_factory: SlideFactory) -> None:
    # Trigger lazy discovery before accessing private source dicts.
    _ = reload_factory.impl_base_package
    tpl_path = reload_factory._template_sources["sample"]
    tpl_path.write_text(
        textwrap.dedent(
            """
            from demo_pkg.factory import app
            from slides_factory.template_input import TemplateInput

            class SampleInput(TemplateInput):
                title: str

            @app.template("sample", name="Sample Reloaded")
            def sample(slide, ctx, data: SampleInput) -> None:
                slide.shapes.add_textbox(0, 0, 100, 100).text = data.title + "!"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    reload_modules(["demo_pkg.templates.sample"])
    assert reload_factory.get_template("sample").name == "Sample Reloaded"
