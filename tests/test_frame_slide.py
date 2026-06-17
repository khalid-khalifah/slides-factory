"""Tests for frame-only slides (cover/closing) and layout blocking."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from slides_factory import document
from slides_factory.frame import get_frame
from slides_factory.render_context import RenderContext


def test_add_frame_slide_round_trip(tmp_path: Path, minimal_brand_yaml: Path):
    output = tmp_path / "cover.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    document.add_frame_slide(prs, "cover", {})
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0)
    assert info["kind"] == "frame"
    assert info["frame_id"] == "cover"
    assert info["template_id"] is None


def test_layout_blocked_on_no_playground_frame(tmp_path: Path, minimal_brand_yaml: Path):
    output = tmp_path / "blocked.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    with pytest.raises(ValueError, match="does not allow grid layout"):
        document.add_layout_slide(
            prs,
            {"grid": "grid-cols-1", "cells": []},
            frame="cover",
        )


def test_playground_box_raises_when_layout_disallowed():
    frame = get_frame("cover")
    ctx = RenderContext.from_presentation(Presentation(), rtl=False, locale="en")
    with pytest.raises(ValueError, match="does not allow layout content"):
        frame.playground_box(ctx)
