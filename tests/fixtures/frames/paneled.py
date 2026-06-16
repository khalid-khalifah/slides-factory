"""Frame with a declared playground region and an information layer.

Exercises the new frame signature: it accepts FrameInfo and draws a title band,
and declares a playground PctBox that the grid layout renders into.
"""

from pptx.slide import Slide
from pptx.util import Emu

from slides_factory.frame_info import FrameInfo
from slides_factory.layout.pct import PctBox
from slides_factory.render_context import RenderContext
from tests.fixtures.app import app
from tests.fixtures.palettes import TEST_LIGHT


@app.frame(
    "paneled",
    name="Paneled",
    description="Frame with playground + info layer for grid tests",
    palette=TEST_LIGHT,
    playground=PctBox(left=10, top=25, width=80, height=65),
)
def paneled(slide: Slide, ctx: RenderContext, info: FrameInfo) -> None:
    if info.title:
        textbox = slide.shapes.add_textbox(
            Emu(0), Emu(0), Emu(ctx.slide_width), Emu(int(ctx.slide_height * 0.15))
        )
        textbox.text_frame.text = info.title
    if info.page_number is not None:
        footer = slide.shapes.add_textbox(
            Emu(0),
            Emu(int(ctx.slide_height * 0.92)),
            Emu(ctx.slide_width),
            Emu(int(ctx.slide_height * 0.08)),
        )
        footer.text_frame.text = str(info.page_number)
