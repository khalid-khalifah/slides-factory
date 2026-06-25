# Skill 04 — Defining Templates

Templates define the **content** of a slide. There are two flavors:

1. **Class-based (recommended)** — Subclass `Template` and declare cells with
   `@at` decorators. The grid layout and element kinds are inferred from class
   metadata. Input models are auto-generated.
2. **Function-based** — A free-form render function `(slide, ctx, data)` for
   slides that don't fit a grid pattern (e.g., charts, cover pages).

---

## Option A: Class-Based Templates (Recommended)

### Basic Template

```python
from slides_factory.templating import Template, at
from my_slides import app


@app.template(
    "kpi",
    name="KPI Dashboard",
    description="Title over a KPI metrics card.",
    grid="grid-cols-1 grid-rows-[auto_1fr] gap-4 p-6",
)
class Kpi(Template):
    @at(kind="text")
    def heading(self): ...

    @at(kind="card")
    def revenue(self): ...
```

**What happens when you register this:**

1. `registration.py` scans the class for `@at`-decorated methods and their
   corresponding element kinds (`text` → `TextProps`, `card` → `CardProps`).
2. It builds a composite `input_model` that merges:

   ```
   {
       "title": str | None,        # template chrome (shared)
       "subtitle": str | None,
       "heading": TextProps,       # from @at method name → element kind
       "revenue": CardProps,
       "frame_style": dict | None, # optional frame styling
       "styles": dict | None,      # per-cell style overrides
   }
   ```

3. `build(data)` converts validated data into a `Layout` with one `CellSpec`
   per `@at` method.

### Input JSON

```json
{
    "title": "Q3 Performance",
    "heading": {"text": "Revenue Growth"},
    "revenue": {"title": "Revenue", "value": "$1.2M", "body": "+12% YoY"}
}
```

### Grid CSS Syntax

The `grid` string uses Tailwind-style CSS classes:

| Class | Meaning |
|-------|---------|
| `grid-cols-1` | 1 column |
| `grid-cols-2` | 2 equal columns |
| `grid-cols-[200px_1fr]` | Fixed + flexible columns |
| `grid-rows-[auto_1fr]` | Auto-height header + fill remaining |
| `gap-4` | 4pt gap between cells |
| `p-6` | 6pt padding inside each cell |

### Cell Placement

By default, cells are placed in declaration order. Override with placement
strings on `@at`:

```python
class Dashboard(Template):
    grid = "grid-cols-2 grid-rows-2 gap-4"

    @at("col-span-2", kind="text")     # spans both columns
    def header(self): ...

    @at(kind="card")
    def left_card(self): ...

    @at(kind="card")
    def right_card(self): ...

    @at("col-span-2", kind="card")     # full-width row
    def bottom_card(self): ...
```

### Per-Cell Styles

Templates also accept optional `styles` in their input to override the default
style of individual cells:

```json
{
    "title": "Dashboard",
    "header": {"text": "Metrics"},
    "left_card": {"title": "Sales", "value": "$500K"},
    "right_card": {"title": "Users", "value": "12K"},
    "styles": {
        "left_card": {"background_color": "secondary:0"},
        "right_card": {"background_color": "main:0"}
    }
}
```

### Default Frame

Templates can declare a preferred frame:

```python
@app.template(
    "section",
    name="Section Header",
    description="Full-bleed section divider",
    grid="grid-cols-1 grid-rows-1",
    default_frame="section",        # ← prefer this frame
)
class Section(Template):
    @at("col-span-1", kind="text")
    def title(self): ...
```

If the caller doesn't specify a frame, `resolve_frame_id` picks:
CLI override > stored > **template default** > brand default > "basic".

---

## Option B: Function-Based Templates

Use this for slides that need custom layout logic (charts, free-form designs):

```python
from pydantic import BaseModel, Field
from pptx.slide import Slide
from slides_factory.render_context import RenderContext
from slides_factory.template import SlideTemplate
from my_slides import app


class CoverData(BaseModel):
    """Input model for the cover slide."""
    title: str = "Untitled"
    subtitle: str = ""
    date: str = ""


@app.template(
    "cover",
    name="Cover",
    description="Full-bleed cover slide with title and date",
    extract=lambda slide: {"title": "Foo", "subtitle": "", "date": ""},
)
def cover(slide: Slide, ctx: RenderContext, data: CoverData) -> None:
    """Draw a custom cover slide — no grid involved."""
    from pptx.util import Pt, Emu
    from pptx.enum.text import PP_ALIGN
    from slides_factory.color_utils import hex_to_rgb
    from slides_factory.styling import theme

    # Title centered vertically at 40%
    title_top = int(ctx.slide_height * 0.35)
    tb = slide.shapes.add_textbox(
        int(ctx.slide_width * 0.1), title_top,
        int(ctx.slide_width * 0.8), int(ctx.slide_height * 0.15),
    )
    tb.text_frame.text = data.title
    tb.text_frame.paragraphs[0].font.size = Pt(36)
    tb.text_frame.paragraphs[0].font.bold = True
    tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Subtitle below
    if data.subtitle:
        stb = slide.shapes.add_textbox(
            int(ctx.slide_width * 0.15), title_top + int(ctx.slide_height * 0.12),
            int(ctx.slide_width * 0.7), int(ctx.slide_height * 0.1),
        )
        stb.text_frame.text = data.subtitle

    # Date at the bottom
    date_tb = slide.shapes.add_textbox(
        int(ctx.slide_width * 0.1), int(ctx.slide_height * 0.85),
        int(ctx.slide_width * 0.8), int(ctx.slide_height * 0.08),
    )
    date_tb.text_frame.text = data.date
    date_tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
```

**Signature rules** — the framework detects these automatically:

| Signature | Use case |
|-----------|----------|
| `(slide, ctx, data)` | Free-form render (data is your validated model) |
| `(slide, ctx)` | Templates that don't need input data |

## Choosing Between the Two

| Class-based (`Template`) | Function-based (`@app.template` on a function) |
|------------------------|-----------------------------------------------|
| Grid-layout slides (KPI, agenda, section) | Free-form slides (cover, charts, custom art) |
| Auto-inferred input model | Manual Pydantic model required |
| Elements are reusable across templates | Everything is hand-drawn |
| Style overrides per cell | Style must be handled manually |
| Easier to maintain | More flexible but more code |

## Template Discovery

Templates are registered when their module is imported. Discovery is
**automatic**: any module placed under `my_slides/templates/` is imported
lazily on first catalog access:

```python
# my_slides/__init__.py
# No explicit discovery call needed — templates/ is auto-discovered
```

```python
# my_slides/templates/kpi.py
from my_slides import app

@app.template("kpi", ...)
class Kpi(Template):
    ...
```

No explicit import of `kpi.py` is needed — the framework discovers it
automatically from the `templates/` subpackage. The same applies to
`frames/` and `elements/` subpackages.
