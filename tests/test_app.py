"""Edge cases for SlideFactory catalog and discovery."""

from __future__ import annotations

import pytest

from tests.fixtures.app import app as _core_app


def test_catalog_lists_test_fixtures():
    template_ids = {t.id for t in _core_app.list_templates()}
    frame_ids = {f.id for f in _core_app.list_frames()}
    assert template_ids == {"paired", "simple", "strict"}
    assert frame_ids == {"alt", "chrome", "cover", "paneled", "plain"}


def test_get_unknown_template_lists_available_ids():
    with pytest.raises(KeyError, match="Unknown template 'missing'"):
        _core_app.get_template("missing")


def test_get_unknown_frame_lists_available_ids():
    with pytest.raises(KeyError, match="Unknown frame 'missing'"):
        _core_app.get_frame("missing")


def test_search_templates_matches_name_and_description():
    by_name = _core_app.search_templates("simple")
    assert {t.id for t in by_name} == {"simple"}
    assert _core_app.search_templates("no-match-xyz") == []


def test_list_templates_filters_by_tag():
    content = {t.id for t in _core_app.list_templates(tag="content")}
    assert content == {"simple"}
    test_only = {t.id for t in _core_app.list_templates(tag="test")}
    assert test_only == {"simple", "strict"}
    assert _core_app.list_templates(tag="missing-tag") == []


def test_list_tags_returns_sorted_unique_tags():
    assert _core_app.list_tags() == ["content", "test"]


def test_search_templates_matches_tags():
    matches = _core_app.search_templates("content")
    assert {t.id for t in matches} == {"simple"}


def test_auto_discover_skips_underscore_modules():
    template_ids = {t.id for t in _core_app.list_templates()}
    assert "_ignored" not in template_ids
