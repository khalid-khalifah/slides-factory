"""Isolated SlideFactory used only by tests/core (no MIM dependency)."""

from slides_factory.app import SlideFactory

app = SlideFactory("test-core")
app.discover_templates("tests.fixtures.templates")
app.discover_frames("tests.fixtures.frames")
