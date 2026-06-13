"""No-op frame for core tests."""

from pptx.slide import Slide

from slides_factory.render_context import RenderContext
from tests.fixtures.app import app
from tests.fixtures.palettes import TEST_LIGHT


@app.frame(
    "plain",
    name="Plain",
    description="No-op test frame",
    palette=TEST_LIGHT,
)
def plain(slide: Slide, ctx: RenderContext) -> None:
    """Frame shell with palette only — no background render."""
