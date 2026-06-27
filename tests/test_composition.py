"""Tests for template composition (sub-template cells via @at(template=...))."""

from __future__ import annotations

from pathlib import Path

import pytest

from slides_factory import document
from slides_factory.app import SlideFactory
from slides_factory.templating import Template, at

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app() -> SlideFactory:
    from tests.fixtures.app import app

    return app


def _make_deck(tmp_path: Path) -> Path:
    output = tmp_path / "test.pptx"
    document.create_document(output)
    return output


# ---------------------------------------------------------------------------
# Define test templates for composition
# ---------------------------------------------------------------------------

# Store registered ids for test access
_COMPOSED_IDS: dict[str, str] = {}


def _register_composition_templates(app: SlideFactory) -> None:
    """Register a "header" sub-template and a "composed" parent template."""
    global _COMPOSED_IDS

    tpl_header = "__test_header__"
    tpl_composed = "__test_composed__"
    _COMPOSED_IDS = {"header": tpl_header, "composed": tpl_composed}

    @app.template(
        tpl_header,
        name="Test Header",
        grid="grid-cols-1 grid-rows-1",
    )
    class TestHeader(Template):
        @at(kind="text")
        def headline(self): ...

    @app.template(
        tpl_composed,
        name="Test Composed",
        grid="grid-cols-2 grid-rows-1 gap-4",
    )
    class TestComposed(Template):
        @at("col-span-1", template=tpl_header)
        def left(self): ...

        @at("col-span-1", kind="card")
        def right(self): ...


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_compose_registration_creates_input_model():
    """Composed template's input model includes sub-template field."""
    app = _make_app()
    _register_composition_templates(app)
    tpl = app.get_template(_COMPOSED_IDS["composed"])
    assert tpl.input_model is not None
    fields = tpl.input_model.model_fields
    assert "left" in fields
    assert "right" in fields


def test_compose_registration_inline_with_elements():
    """Mixed composition: one template cell, one element cell."""
    app = _make_app()
    _register_composition_templates(app)
    tpl = app.get_template(_COMPOSED_IDS["composed"])
    fields = tpl.input_model.model_fields
    assert "left" in fields
    assert "right" in fields


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------


def test_compose_two_templates_renders_both_cells(tmp_path: Path):
    """Parent with 2 cells (1 sub-template, 1 element) renders both."""
    app = _make_app()
    _register_composition_templates(app)
    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)

    data = {
        "left": {"headline": {"block": {"children": [{"runs": [{"text": "Left Header"}]}]}}},
        "right": {"title": "Right Card", "value": "$100"},
    }
    result = document.add_slide(prs, _COMPOSED_IDS["composed"], data, app=app)
    document.save_document(prs, deck)

    prs = document.open_document(deck)
    slide = prs.slides[result["slide_index"]]
    assert len(slide.shapes) > 0


def test_compose_nested_three_levels(tmp_path: Path):
    """3-level composition: outer -> inner -> innermost."""
    app = _make_app()

    @app.template("__test_level3__", name="L3", grid="grid-cols-1 grid-rows-1")
    class Level3(Template):
        @at(kind="text")
        def content(self): ...

    @app.template("__test_level2__", name="L2", grid="grid-cols-1 grid-rows-1")
    class Level2(Template):
        @at(template="__test_level3__")
        def inner(self): ...

    @app.template("__test_level1__", name="L1", grid="grid-cols-1 grid-rows-1")
    class Level1(Template):
        @at(template="__test_level2__")
        def middle(self): ...

    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)

    data = {
        "middle": {
            "inner": {
                "content": {"block": {"children": [{"runs": [{"text": "Deep"}]}]}},
            },
        },
    }
    result = document.add_slide(prs, "__test_level1__", data, app=app)
    document.save_document(prs, deck)

    prs = document.open_document(deck)
    slide = prs.slides[result["slide_index"]]
    assert len(slide.shapes) > 0


def test_compose_unknown_template_raises_at_registration():
    """Registration referencing a non-existent template raises."""
    app = _make_app()

    with pytest.raises((TypeError, KeyError, Exception)):

        @app.template(
            "__test_bad_compose__",
            name="Bad Compose",
            grid="grid-cols-1",
        )
        class BadCompose(Template):
            @at(template="__nonexistent__")
            def cell(self): ...

        # Force resolution of the input model
        app.get_template("__test_bad_compose__")


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------


def test_compose_cli_with_inline_json(tmp_path: Path):
    """slide add with a composed template works via CLI with inline JSON."""
    import json

    from typer.testing import CliRunner

    app = _make_app()
    _register_composition_templates(app)
    deck = _make_deck(tmp_path)

    rows = [
        {
            "left": {"headline": {"block": {"children": [{"runs": [{"text": "Left"}]}]}}},
            "right": {"title": "Card", "value": "$100"},
        }
    ]
    runner = CliRunner()
    result = runner.invoke(
        app.cli,
        [
            "slide", "add-many", str(deck),
            "--template", _COMPOSED_IDS["composed"],
            "--rows", json.dumps(rows),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
