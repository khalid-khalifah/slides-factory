"""Frame-only cover fixture with no playground (for frame slide tests)."""

from pptx.util import Emu

from tests.fixtures.app import app
from tests.fixtures.palettes import TEST_LIGHT


@app.frame(
    "cover",
    name="Cover",
    description="Frame-only cover with no playground",
    palette=TEST_LIGHT,
    allows_layout=False,
)
def cover(slide, ctx, info=None):
    slide.shapes.add_textbox(
        Emu(0), Emu(0), Emu(ctx.slide_width), Emu(int(ctx.slide_height * 0.2))
    )
