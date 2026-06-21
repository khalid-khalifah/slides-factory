"""Frame that adds a rectangle for lock integration tests."""

from pptx.enum.shapes import MSO_SHAPE
from pptx.slide import Slide

from slides_factory.color_utils import hex_to_rgb
from slides_factory.render_context import RenderContext
from tests.fixtures.app import app
from tests.fixtures.palettes import TEST_LIGHT


@app.frame(
    "chrome",
    name="Chrome",
    description="Adds a full-slide rectangle for lock tests",
    palette=TEST_LIGHT,
)
def chrome(slide: Slide, ctx: RenderContext) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, ctx.slide_width, ctx.slide_height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = hex_to_rgb(ctx.palette.main[0])
    shape.line.fill.background()
