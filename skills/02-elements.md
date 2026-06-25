# Skill 02 — Defining Elements

Elements are the atomic drawable units placed into grid cells. They implement a
three-part contract: a **props model** (what data goes into the layout YAML), an
optional **style model** (visual appearance tokens), and a **render function**
that draws onto a slide.

## The Element Protocol

```python
class Element(ABC):
    kind: ClassVar[str]                    # unique identifier (e.g. "chart")
    props_model: ClassVar[type[BaseModel]] # validates cell data
    style_model: ClassVar[type[BaseModel]] # validates cell style (default: EmptyStyle)

    def render(
        self,
        slide: Slide,
        box: Box,           # (left, top, width, height) in EMU
        props: BaseModel,   # validated props_model instance
        style: BaseModel,   # validated style_model instance
        ctx: RenderContext, # palette, brand, rtl, locale
    ) -> None: ...
```

## Via the `@app.element` Decorator

This is the standard approach — it mirrors `@app.template` and `@app.frame`:

```python
from pydantic import BaseModel, Field
from pptx.slide import Slide
from slides_factory.elements.base import Box
from slides_factory.render_context import RenderContext


# 1. Props model — the data that goes into layout YAML / JSON
class ProgressBarProps(BaseModel):
    """A horizontal bar showing progress toward a target."""
    label: str = ""
    current: float = 0.0
    target: float = 100.0
    unit: str = ""


# 2. Style model — visual tokens (optional, defaults to EmptyStyle)
class ProgressBarStyle(BaseModel):
    bar_color: str = "highlight"
    background_color: str = "primary"
    label_size: str = "body"


# 3. Render function — draws the element
def render_progress_bar(
    slide: Slide,
    box: Box,
    props: ProgressBarProps,
    style: ProgressBarStyle,
    ctx: RenderContext,
) -> None:
    """Draw a labeled progress bar."""
    from pptx.util import Emu
    from slides_factory.color_utils import hex_to_rgb
    from slides_factory.styling import theme

    left, top, width, height = box
    bar_height = height // 3
    pct = min(props.current / props.target, 1.0) if props.target > 0 else 0.0

    # Background bar
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top + bar_height, width, bar_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = hex_to_rgb(
        theme.resolve_style_color(style.background_color, ctx)
    )
    bg.line.fill.background()

    # Filled portion
    fill = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        left, top + bar_height,
        int(width * pct), bar_height,
    )
    fill.fill.solid()
    fill.fill.fore_color.rgb = hex_to_rgb(
        theme.resolve_style_color(style.bar_color, ctx)
    )
    fill.line.fill.background()

    # Label
    label_text = f"{props.label} ({props.current:.0f}/{props.target:.0f} {props.unit})"
    textbox = slide.shapes.add_textbox(left, top, width, bar_height)
    textbox.text_frame.text = label_text
```

Register it in your app setup:

```python
# my_slides/__init__.py or a dedicated module
app.element(
    "progress_bar",
    props_model=ProgressBarProps,
    style_model=ProgressBarStyle,
)(render_progress_bar)
```

## Via `element_from_function` (Programmatic)

Use this when you want to keep registration separate from definition:

```python
from slides_factory.elements.base import element_from_function

progress_bar_element = element_from_function(
    render_progress_bar,
    kind="progress_bar",
    props_model=ProgressBarProps,
    style_model=ProgressBarStyle,
)

# Later, in app setup:
app._elements["progress_bar"] = progress_bar_element
```

## Built-in Helpers

| Helper | What it does |
|--------|-------------|
| `theme.font_size_pt("body")` | Resolve a size token to point value |
| `theme.resolve_style_color("primary", ctx)` | Resolve a color token → hex string |
| `theme.radius("md")` | Resolve a radius token → float |
| `style_paragraph(p, ctx, size_pt=..., bold=..., color_token=..., align=...)` | Style one paragraph's runs |
| `apply_shape_font(shape, ctx, font_key)` | Set font family on a shape |
| `hex_to_rgb("#123456")` | Hex → `pptx` `RGBColor` |
| `is_brand_fill_ref("main:0")` | Check if a token references brand (vs palette) |

## Reference: Built-in Elements

Study these in `slides_factory/elements/`:

- **`text.py`** — Simple labeled + bullet text box. Good starting reference.
- **`card.py`** — Filled rounded rectangle with title/value/body + brand-aware
  color logic. Shows how to handle brand fill references.

## Grid Cell Integration

Once registered, your element can be used in any template:

```python
class Kpi(Template):
    grid = "grid-cols-1 grid-rows-[auto_1fr]"

    @at(kind="text")
    def heading(self): ...

    @at(kind="progress_bar")     # ← your custom element
    def progress(self): ...
```

Input JSON for that template:

```json
{
    "heading": {"text": "Q3 Progress"},
    "progress": {"label": "Revenue", "current": 75, "target": 100, "unit": "M"}
}
```
