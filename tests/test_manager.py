"""Tests for SlideManager lifecycle helpers."""

from __future__ import annotations

from pathlib import Path

from slides_factory.core.manager import SlideManager
from slides_factory.core.session import PresentationSession


def _prs():
    theme_path = Path("themes/default.pptx")
    session = PresentationSession.create_new(
        default_theme_provider=lambda: theme_path,
        delete_slide_callback=lambda p, i: SlideManager(p).delete_slide(i),
    )
    return session.presentation


def test_insert_slide_places_at_index():
    prs = _prs()
    mgr = SlideManager(prs)
    layout = prs.slide_layouts[0]
    prs.slides.add_slide(layout)
    prs.slides.add_slide(layout)
    slide = mgr.insert_slide(layout, 0)
    assert slide == prs.slides[0]
    assert len(prs.slides) == 3


def test_clear_slide_shapes_removes_custom_shapes():
    prs = _prs()
    mgr = SlideManager(prs)
    layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    slide.shapes.add_textbox(0, 0, 100, 100)
    assert len([s for s in slide.shapes if not s.is_placeholder]) >= 1
    mgr.clear_slide_shapes(slide)
    assert len([s for s in slide.shapes if not s.is_placeholder]) == 0


def test_remove_slide_raises_on_bad_index():
    prs = _prs()
    mgr = SlideManager(prs)
    try:
        mgr.remove_slide(0)
        raised = False
    except IndexError:
        raised = True
    assert raised
