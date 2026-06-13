"""Tests for the preview CLI launcher."""

from __future__ import annotations

import pytest

from slides_factory.preview.run import run_preview


def test_run_preview_requires_impl_module(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "streamlit", object())
    with pytest.raises(RuntimeError, match="Preview is not configured"):
        run_preview(impl_module=None)
