"""Must not be discovered — modules starting with _ are skipped.

Uses a legacy plain ``title: str`` signature (pre-TemplateInput) to ensure
discovery still skips underscore-prefixed modules.
"""

from pptx.slide import Slide

from slides_factory.render_context import RenderContext
from tests.fixtures.app import app


@app.template("_ignored", name="Ignored")
def _ignored(slide: Slide, ctx: RenderContext, title: str) -> None:
    pass
