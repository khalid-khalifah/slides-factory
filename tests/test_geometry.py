"""Tests for the Box geometry type and element sizing constraints."""

from __future__ import annotations

import pytest
from pptx.util import Emu
from pydantic import BaseModel

from slides_factory.elements.base import element_from_function
from slides_factory.geometry import Box
from slides_factory.templating import Template, at
from tests.fixtures.app import app as _app_fixture


# Minimal Pydantic model for test elements
class _DummyModel(BaseModel):
    pass


def _dummy_render(slide, box, props, style, ctx) -> None:
    pass


# ---------------------------------------------------------------------------
# Box class
# ---------------------------------------------------------------------------

def test_box_tuple_unpack():
    b = Box(10, 20, 100, 200)
    left, top, width, height = b
    assert left == 10
    assert top == 20
    assert width == 100
    assert height == 200


def test_box_tuple_equality():
    b = Box(10, 20, 100, 200)
    assert b == (10, 20, 100, 200)
    assert b != (10, 20, 99, 200)


def test_box_equality_same_type():
    assert Box(0, 0, 100, 100) == Box(0, 0, 100, 100)
    assert Box(0, 0, 100, 100) != Box(0, 0, 200, 100)


def test_box_properties():
    b = Box(10, 20, 100, 200)
    assert b.right == 110
    assert b.bottom == 220
    assert b.center_x == 60.0
    assert b.center_y == 120.0


def test_box_inset():
    b = Box(0, 0, 100, 100)
    b2 = b.inset(10, 20)
    assert b2 == (10, 20, 80, 60)
    assert b == (0, 0, 100, 100)


def test_box_with_margin():
    b = Box(0, 0, 100, 100)
    b2 = b.with_margin(top=5, right=10, bottom=15, left=20)
    assert b2 == (20, 5, 70, 80)


def test_box_immutable():
    b = Box(0, 0, 100, 100)
    with pytest.raises((AttributeError, BaseException)):
        b.left = 5  # type: ignore[misc]


def test_box_hashable():
    s = {Box(0, 0, 100, 100), Box(0, 0, 100, 100)}
    assert len(s) == 1


# ---------------------------------------------------------------------------
# Element constraint registration
# ---------------------------------------------------------------------------

def test_element_registration_with_constraints():
    """element_from_function propagates min/max to the element."""
    el = element_from_function(
        _dummy_render,
        kind="__test__",
        props_model=_DummyModel,
        min_width=Emu(1),
        max_height=Emu(2),
    )
    assert el.min_width == Emu(1)
    assert el.max_width is None
    assert el.min_height is None
    assert el.max_height == Emu(2)


# ---------------------------------------------------------------------------
# Template _min_box / _max_box
# ---------------------------------------------------------------------------

def test_template_min_box_with_constrained_element():
    """Template with an element that has min_width returns that as _min_box."""
    app = _app_fixture

    el = element_from_function(
        _dummy_render,
        kind="__constrained__",
        props_model=_DummyModel,
        min_width=Emu(500),
        min_height=Emu(300),
    )
    app._elements["__constrained__"] = el

    @app.template("__tpl_min__", name="Min Test", grid="grid-cols-1")
    class MinTpl(Template):
        @at(kind="__constrained__")
        def cell(self): ...

    min_box = MinTpl._min_box()
    assert min_box is not None
    assert min_box.width == Emu(500)
    assert min_box.height == Emu(300)


def test_template_min_box_none_when_no_constraints():
    """Template with no constrained elements returns None from _min_box."""
    app = _app_fixture

    @app.template("__tpl_no_min__", name="No Min", grid="grid-cols-1")
    class NoMinTpl(Template):
        @at(kind="text")
        def cell(self): ...

    assert NoMinTpl._min_box() is None


def test_template_max_box_with_element():
    """Template with constrained max returns that as _max_box."""
    app = _app_fixture

    el = element_from_function(
        _dummy_render,
        kind="__max_constrained__",
        props_model=_DummyModel,
        max_width=Emu(800),
    )
    app._elements["__max_constrained__"] = el

    @app.template("__tpl_max__", name="Max Test", grid="grid-cols-1")
    class MaxTpl(Template):
        @at(kind="__max_constrained__")
        def cell(self): ...

    max_box = MaxTpl._max_box()
    assert max_box is not None
    assert max_box.width == Emu(800)
    assert max_box.height == 0  # no height constraint


def test_template_max_box_none_when_no_constraints():
    """Template with no max-constrained elements returns None."""
    app = _app_fixture

    @app.template("__tpl_no_max__", name="No Max", grid="grid-cols-1")
    class NoMaxTpl(Template):
        @at(kind="text")
        def cell(self): ...

    assert NoMaxTpl._max_box() is None
