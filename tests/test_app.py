"""Edge cases for SlideFactory catalog and discovery."""

from __future__ import annotations

import importlib

import pytest
from pptx.slide import Slide

from slides_factory.app import SlideFactory, get_app
from slides_factory.render_context import RenderContext


def test_get_app_requires_configured_factory():
    original = importlib.import_module("slides_factory.app")._active_app
    importlib.import_module("slides_factory.app")._active_app = None
    try:
        with pytest.raises(RuntimeError, match="No slide factory app configured"):
            get_app()
    finally:
        importlib.import_module("slides_factory.app")._active_app = original


def test_catalog_lists_test_fixtures():
    app = get_app()
    template_ids = {t.id for t in app.list_templates()}
    frame_ids = {f.id for f in app.list_frames()}
    assert template_ids == {"paired", "simple", "strict"}
    assert frame_ids == {"alt", "chrome", "plain"}


def test_get_unknown_template_lists_available_ids():
    with pytest.raises(KeyError, match="Unknown template 'missing'"):
        get_app().get_template("missing")


def test_get_unknown_frame_lists_available_ids():
    with pytest.raises(KeyError, match="Unknown frame 'missing'"):
        get_app().get_frame("missing")


def test_search_templates_matches_name_and_description():
    app = get_app()
    by_name = app.search_templates("simple")
    assert {t.id for t in by_name} == {"simple"}
    assert app.search_templates("no-match-xyz") == []


def test_list_templates_filters_by_tag():
    app = get_app()
    content = {t.id for t in app.list_templates(tag="content")}
    assert content == {"simple"}
    test_only = {t.id for t in app.list_templates(tag="test")}
    assert test_only == {"simple", "strict"}
    assert app.list_templates(tag="missing-tag") == []


def test_list_tags_returns_sorted_unique_tags():
    app = get_app()
    assert app.list_tags() == ["content", "test"]


def test_search_templates_matches_tags():
    app = get_app()
    matches = app.search_templates("content")
    assert {t.id for t in matches} == {"simple"}


def test_discover_templates_is_idempotent():
    app = get_app()
    before = {t.id for t in app.list_templates()}
    app.discover_templates("tests.fixtures.templates")
    after = {t.id for t in app.list_templates()}
    assert before == after


def test_discover_skips_underscore_modules():
    template_ids = {t.id for t in get_app().list_templates()}
    assert "_ignored" not in template_ids
