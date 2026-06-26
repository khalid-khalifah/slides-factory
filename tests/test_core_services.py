"""Tests for core LayoutEngine and legacy grid lifecycle coverage."""

from pathlib import Path

import pytest

from slides_factory.core.engine import LayoutEngine
from slides_factory.core.grid import GridSlideService
from slides_factory.core.manager import SlideManager
from slides_factory.core.session import PresentationSession


@pytest.fixture
def prs():
    """Provide a basic presentation shell."""
    theme_path = Path("themes/default.pptx")

    session = PresentationSession.create_new(
        default_theme_provider=lambda: theme_path,
        delete_slide_callback=lambda p, i: SlideManager(p).delete_slide(i),
    )
    return session.presentation


def test_core_grid_lifecycle(prs, app):
    """GridSlideService covers new slide, add cell, and grid update flows."""
    svc = GridSlideService(prs, app=app)
    result = svc.new_grid_slide(grid="grid-cols-2", frame_info={"title": "Test Grid"})
    assert result["data"]["grid"] == "grid-cols-2"

    svc.add_cell(
        0,
        kind="text",
        at="col-start-1",
        props={"text": "Hello"},
    )
    spec = svc.require_grid_data(0)
    assert len(spec["cells"]) == 1

    svc.set_slide(0, grid="grid-cols-1")
    spec = svc.require_grid_data(0)
    assert spec["grid"] == "grid-cols-1"


def test_layout_engine_ensure_allows_layout(prs, app):
    """Test that frames not allowing layout raise ValueError."""
    engine = LayoutEngine(prs, app=app)
    from slides_factory.frame import get_frame

    frame_tpl = get_frame(app, "cover")
    with pytest.raises(ValueError, match="does not allow grid layout"):
        engine.ensure_frame_allows_layout(frame_tpl)
