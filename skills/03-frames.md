# Skill 03 — Defining Frames

Frames are **page shells** — they paint backgrounds, draw fixed shapes, and
optionally render an information layer (title, subtitle, date, logo) before the
template fills the content region (the *playground*).

## The Frame Contract

```python
class FrameTemplate(ABC):
    id: ClassVar[str]                    # unique identifier, e.g. "branded"
    name: ClassVar[str]
    description: ClassVar[str]
    palette: ClassVar[SlidePalette]      # default palette for this frame
    playground: ClassVar[PctBox | None]  # body region (content goes here)
    frame_input: ClassVar[type[BaseModel]] = EmptyFrameInput   # info model
    frame_style: ClassVar[type[BaseModel]] = EmptyStyle        # style model
    allows_layout: ClassVar[bool] = True

    def render(
        self,
        slide: Slide,
        ctx: RenderContext,
        info: BaseModel | None = None,      # validated frame_input
        style: BaseModel | None = None,     # validated frame_style
    ) -> None: ...
```

## Via `@app.frame` Decorator

### Minimal Frame (No Input, No Style)

```python
from pptx.slide import Slide
from slides_factory.render_context import RenderContext
from slides_factory.color_utils import hex_to_rgb

from my_slides import app
from tests.fixtures.palettes import MY_PALETTE


@app.frame(
    "white",
    name="White",
    description="Simple white background with a thin bottom border",
    palette=MY_PALETTE,
)
def white(slide: Slide, ctx: RenderContext) -> None:
    """Paint a white background and a bottom accent line."""
    from pptx.enum.shapes import MSO_SHAPE

    # Full-slide background
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, ctx.slide_width, ctx.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = hex_to_rgb("#FFFFFF")
    bg.line.fill.background()

    # Accent line at the bottom
    line_h = int(ctx.slide_height * 0.008)
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, ctx.slide_height - line_h,
        ctx.slide_width, line_h,
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = hex_to_rgb(ctx.palette.highlight)
    accent.line.fill.background()
```

### Frame with Info Input (Title, Subtitle, Logo)

```python
from pydantic import BaseModel, Field
from pptx.slide import Slide
from slides_factory.render_context import RenderContext
from slides_factory.layout.pct import resolve_logo_placement

from my_slides import app


class BrandedFrameInfo(BaseModel):
    """Information layer for the branded frame."""
    title: str = ""
    subtitle: str = ""
    show_logo: bool = True


@app.frame(
    "branded",
    name="Branded",
    description="Full brand background with title bar and logo",
    palette=MY_PALETTE,
    frame_input=BrandedFrameInfo,
)
def branded(slide: Slide, ctx: RenderContext, info: BrandedFrameInfo) -> None:
    """Draw brand background, title bar, and optional logo."""
    import math

    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Pt
    from slides_factory.color_utils import hex_to_rgb
    from slides_factory.styling import theme

    # Background fill from brand or palette
    bg_color = theme.resolve_style_color("main:0", ctx)
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, ctx.slide_width, ctx.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = hex_to_rgb(bg_color)
    bg.line.fill.background()

    # Title band — lighter stripe at the top
    band_h = int(ctx.slide_height * 0.18)
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, ctx.slide_width, band_h
    )
    band.fill.solid()
    band_color = theme.resolve_style_color("basic:0", ctx)
    band.fill.fore_color.rgb = hex_to_rgb(band_color)
    band.line.fill.background()

    # Title text
    if info.title:
        tb = slide.shapes.add_textbox(
            int(ctx.slide_width * 0.06), int(band_h * 0.2),
            int(ctx.slide_width * 0.7), int(band_h * 0.6),
        )
        tb.text_frame.text = info.title
        tb.text_frame.paragraphs[0].font.size = Pt(24)
        tb.text_frame.paragraphs[0].font.bold = True

    # Logo
    if info.show_logo and ctx.brand:
        logo_placed = resolve_logo_placement(ctx, "en")
        if logo_placed:
            slide.shapes.add_picture(
                str(logo_placed.path),
                logo_placed.left, logo_placed.top,
                logo_placed.width, logo_placed.height,
            )
```

### Frame with Style Options

When you want the template to control aspects of the frame's appearance (e.g.
background color variant), declare a `frame_style`:

```python
class SectionStyle(BaseModel):
    background_group: str = "main"
    background_index: int = 0
    accent_position: str = "bottom"      # "top" | "bottom" | "none"


@app.frame(
    "section",
    name="Section Divider",
    description="Full-bleed section header with accent stripe",
    palette=MY_PALETTE,
    frame_style=SectionStyle,
)
def section(slide: Slide, ctx: RenderContext, info: BrandedFrameInfo, style: SectionStyle) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    from slides_factory.color_utils import hex_to_rgb
    from slides_factory.styling import theme

    # Use brand-aware palette when a brand is active
    palette = FrameTemplate.palette_for(ctx, style)

    # Background from style choice
    bg_color = theme.resolve_style_color(f"{style.background_group}:{style.background_index}", ctx)
    bg = slide.shapes.add_shape(...)
    # ... rest of rendering
```

## Key Points

| Concept | Detail |
|---------|--------|
| **Signature arity** | `(slide, ctx)`, `(slide, ctx, info)`, or `(slide, ctx, info, style)` — detected automatically |
| **Playground** | The `PctBox` region where template content is placed. Use `playground_box(ctx)` to resolve to EMU |
| **`allows_layout`** | Set `False` for frames that cover the full slide (no room for template content) |
| **Palette derivation** | `palette_for(ctx, style)` derives a brand-aware palette when a brand theme is active |
| **Logo placement** | Use `resolve_logo_placement(ctx, locale)` from `slides_factory.layout.pct` |

## Reference

See the test fixture frames in `tests/fixtures/frames/` for more examples:
- `chrome.py` — Minimal frame with a rectangle
- `tests/fixtures/frames/cover.py` — Cover with branded palette
