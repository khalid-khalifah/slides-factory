# slides_factory (core)

Brand-agnostic PowerPoint slide engine. Provides abstractions, orchestration, the central **app**, and the generic CLI — **no concrete templates or frames**.

Implementations (e.g. a brand-specific package like `mim-slides`) create an app instance, discover their modules, and expose the CLI entry point. See **Registering an implementation** below.

## What the core provides

- **Document API** — create, open, add/edit/remove slides, embed fonts on save
- **Template protocol** — `SlideTemplate` ABC, optional `default_frame`, `TemplateInput` schemas, JSON schema export
- **Frame protocol** — `FrameTemplate` ABC (requires `palette` ClassVar)
- **SlideFactory** — central app; template/frame **functions** register via `@app.template` / `@app.frame` (FastAPI-style)
- **CLI** — generic Typer commands wired to the active app
- **RenderContext** — RTL, locale, brand, slide dimensions, frame palette
- **SlidePalette** — abstraction for text/highlight/accent colors passed frame → template
- **Brand YAML** — page size, layout %, colors, fonts, logos
- **RTL** — shape mirroring and Arabic complex-script font slots
- **Metadata** — round-trip JSON in speaker notes

## Package layout

```
slides_factory/
├── document.py         # add_slide, edit_slide, save_document, …
├── app.py              # SlideFactoryApp — registry, decorators, CLI
├── template.py         # SlideTemplate ABC (optional default_frame ClassVar)
├── frame.py            # FrameTemplate ABC + resolve_frame_id
├── render_context.py   # RenderContext + with_palette()
├── palette.py          # SlidePalette dataclass + color helpers
├── brand.py            # load_brand(), BrandTheme, colors, fonts, logos
├── brand_doc.py        # Persist brand path on document
├── fonts.py            # Apply brand fonts to runs
├── font_embed.py       # Embed TTF/OTF into .pptx on save
├── logo_assets.py      # Resolve/rasterize logo files
├── pct_layout.py       # Percent-based boxes and logo placement
├── locale.py           # Document RTL/locale in core properties
├── metadata.py         # JSON metadata in speaker notes
├── rtl.py              # RTLLayout — mirror positions, RTL text
└── models.py           # CLIResponse wrapper
```

## Core concepts

### Slide render pipeline

An **implementation** registers templates and frames. The core orchestrates:

```
resolve_frame_id()   # CLI > stored (edit) > template.default_frame > brand.default_frame > fallback
  → get_frame(frame_id)
  → RenderContext.from_presentation(brand, rtl, locale)
  → ctx.with_palette(frame.palette)
  → ctx.with_playground(frame.playground_box(ctx))   # body region for layout content
  → frame.render(slide, ctx, info)  # background + logo + information layer (title, page number)
  → template.render(slide, data, ctx)
  → metadata.write_metadata()
  → save_document()                 # embeds fonts
```

### Frame / Layout / Element — the core

Grid + elements are the **foundation** the engine draws through; templates are a
thin layer built *on top* of them (not the other way around). Layout authoring
stays abstract: you describe structure and style with compact, Tailwind-like
utility classes resolved against a central theme scale.

1. **Frame** — page chrome (background, fixed shapes) plus two capabilities:
   - an **information layer**: the frame receives a `FrameInfo` (`title`,
     `subtitle`, `page_number`, `total_pages`) and draws it. Frames use the
     signature `render(self, slide, ctx, info)`; the legacy `(slide, ctx)` form
     still works (the arity is detected automatically).
   - a **playground**: `playground: ClassVar[PctBox | None]` declares the body
     region where layout content is placed. When a frame omits it — or a deck
     has no brand/frame — a sensible default body region is used.
2. **Layout** — a `Layout` (grid classes + ordered cells, each holding one
   element) is the engine's render contract. `render_layout(slide, layout, ctx)`
   solves the grid inside the playground and draws every element. Columns/rows,
   gaps, padding, spans and placement all come from utility classes. There is no
   "grid template" — the grid is core.
3. **Element** — a registered, drawable unit (`text`, `card`; extend via
   `@app.element`) with its own Pydantic props, styled by utility classes and
   drawn into a grid cell.

A **template** sits above this core: it pairs a typed input model (the
"collective data") with one `@at` cell-method each, builds a `Layout` from
validated data, and renders it through `render_layout` (see *Adding a template*).

#### Utility-class vocabulary

| Scope | Flag | Classes |
|-------|------|---------|
| Grid | `--grid` | `grid-cols-N`, `grid-cols-[2_1_1]`, `grid-rows-N`, `grid-rows-[1_2]`, `gap-K`, `gap-x-K`, `gap-y-K`, `p-K`, `px-K`, `py-K` |
| Cell | `--at` | `col-span-N`, `row-span-N`, `col-start-N`, `row-start-N`, `items-{start,center,end}`, `justify-{start,center,end}` |
| Element | `--style` | `text-{sm,base,lg,xl,2xl,3xl,4xl}`, `font-{normal,medium,semibold,bold}`, `text-{left,center,right}`, `text-{primary,highlight,muted}`, `bg-{main,surface,…}`, `rounded[-{sm,md,lg,xl,full}]`, `border`, `p-K` |

Run `your-slides classes --json` to print this vocabulary at runtime.

Spacing tokens (`K`) resolve to fractions of the region; font tokens to points;
color tokens bind to `SlidePalette` slots (with neutral fallbacks when there is
no brand/frame). Unknown tokens raise a clear error.

#### Building a raw grid slide (flag-driven CLI)

For ad-hoc slides the CLI is an **incremental builder** over a raw `Layout` —
no template needed. An agent creates a slide, then adds one element at a time;
every command prints a `{ ok, data }` envelope (`--json`). (For reusable,
named slides with typed data, register a template instead — see below.)

```bash
# 1. create the deck
your-slides doc create -o deck.pptx --brand brand.yaml

# 2. open a grid slide: --grid is the grid utility string; frame info via flags
your-slides slide new deck.pptx \
  --frame paneled --title "Quarterly Review" --page-number 1 \
  --grid "grid-cols-[2_1] grid-rows-2 gap-4 p-2"

# 3. drop elements into cells: --at = placement, --style = look, --set = props
your-slides el add deck.pptx --index 0 --kind card \
  --at "row-span-2" --style "bg-surface rounded-lg" \
  --set title=Revenue --set value=\$1.2M

your-slides el add deck.pptx --index 0 --kind text \
  --style "text-2xl font-bold text-primary" \
  --set text=Highlights --set bullets="Up 18% YoY" --set bullets="New region live"
```

Repeating `--set key=value` builds a list for list-typed props (e.g. `bullets`).
Edit in place with `el set --cell N`, drop a cell with `el rm --cell N`, and
change grid/frame info with `slide set`. The full spec round-trips through
speaker-note metadata, so `doc get --index 0 --json` returns exactly what was
built. The same helpers are available programmatically:

```python
from slides_factory import document

prs = document.create_document("deck.pptx", brand="brand.yaml")
document.new_grid_slide(prs, frame="paneled", title="Quarterly Review",
                        grid="grid-cols-[2_1] grid-rows-2 gap-4 p-2")
document.add_cell(prs, 0, kind="card", at="row-span-2",
                  style="bg-surface rounded-lg",
                  props={"title": "Revenue", "value": "$1.2M"})
document.add_cell(prs, 0, kind="text", style="text-2xl font-bold text-primary",
                  props={"text": "Highlights", "bullets": ["Up 18% YoY"]})
document.save_document(prs, "deck.pptx")
```

Discover what's available without leaving the CLI: `elements list --json`,
`elements inspect card --json` (full props schema), and `classes --json`.

#### Adding an element kind

```python
from pydantic import BaseModel
from your_impl.app import app

class QuoteProps(BaseModel):
    text: str
    author: str = ""

@app.element("quote", props_model=QuoteProps)
def quote(slide, box, style, props: QuoteProps, ctx) -> None:
    left, top, width, height = box
    tb = slide.shapes.add_textbox(left, top, width, height)
    tb.text_frame.text = f"\u201c{props.text}\u201d\n\u2014 {props.author}"
```

### RenderContext

Every template receives a frozen `RenderContext`:

| Field | Purpose |
|-------|---------|
| `rtl` | Mirror shapes and set RTL text |
| `locale` | Font language tag (`en`, `ar`, …) |
| `slide_width` / `slide_height` | EMU dimensions for layout |
| `brand` | Loaded `BrandTheme` (optional) |
| `palette` | `SlidePalette` from frame (optional) |
| `playground` | Resolved body region `(left, top, width, height)` in EMU for the grid (optional) |

### SlidePalette

Defined in `palette.py`. Implementations assign presets on each frame class:

```python
@dataclass(frozen=True)
class SlidePalette:
    text: str
    highlight: str
    main: tuple[str, ...]
    extras: tuple[str, ...]
    extras_start: int = 0
    extras_end: int | None = None
```

Templates should read `ctx.palette` (helpers in `_helpers.py` apply `palette.text` automatically).

### Brand YAML (generic)

The core loads any brand file matching this shape:

```yaml
name: my-brand
default_frame: basic   # deck-wide fallback only; per-template defaults go on @app.template
page:
  width_in: 13.333
  height_in: 7.5
layout:
  logos:
    en: { right: 4.0, top: 7.5 }
    ar: { left: 4.35, top: 7.5 }
colors:
  main: ["#413258", "#E6E6E6"]
  secondary: ["#1AD9C7", "#BFA19F"]
  basic: ["#FFFFFF", "#000000", …]
fonts:
  title: { file: path/to/font.ttf }
  body:  { file: path/to/font.otf }
logos:
  wordmark: { en: logo_en.svg, ar: logo_ar.svg }
```

Frames use `colors.main[i]` / `colors.secondary[i]` for **background fills**. Text colors come from **frame palettes**, not raw YAML.

## Python API

```python
import your_impl  # registers templates + frames on import

from slides_factory import document, template, frame
from slides_factory.frame import get_frame, list_frames
from slides_factory.brand import load_brand
from slides_factory.render_context import RenderContext

# List registered templates (requires implementation import)
for t in template.list_templates():
    print(t.id)

# Programmatic slide add
prs = document.open_document("deck.pptx")
document.add_slide(prs, "bullets", {"title": "Hi", "bullets": ["a"]}, frame="basic")
document.save_document(prs, "deck.pptx")
```

## Registering an implementation

Like FastAPI: core defines `SlideFactoryApp`; the implementation creates one instance and modules register on import.

In `your_impl/app.py`:

```python
from slides_factory.app import SlideFactory

app = SlideFactory("YourBrand")
app.discover_templates("your_impl.templates")
app.discover_frames("your_impl.frames")
```

CLI entry point (`your_impl/cli/app.py`):

```python
from your_impl.app import app as factory_app
app = factory_app.cli  # setuptools [project.scripts] target
```

### Adding a template (in implementation package)

A template is a **class built on top of the grid+element core**: a typed input
model (the "collective data") plus one `@at` method per cell. Each decorator
carries the cell's placement, element `kind`, and look `style`; the method maps
validated data to that element's props. Calling the template validates JSON,
builds a `Layout`, and renders it through `render_layout`.

```python
from slides_factory.template_input import TemplateInput
from slides_factory.templating import Template, at
from slides_factory.frame_info import FrameInfo
from your_impl.app import app

class KpiInput(TemplateInput):
    heading: str
    revenue: str
    customers: str

@app.template(
    "kpi-duo",
    name="KPI Duo",
    description="A bold heading over two KPI cards side by side.",  # shown in the CLI
    grid="grid-cols-2 grid-rows-[1_2] gap-4",
    default_frame="basic",  # optional — used when --frame is omitted
)
class KpiDuo(Template):
    input_model = KpiInput

    def frame_info(self, data: KpiInput) -> FrameInfo:   # optional: feed the frame
        return FrameInfo(title=data.heading)

    @at("col-span-2", kind="text", style="text-3xl font-bold text-primary")
    def heading(self, data: KpiInput) -> dict:
        return {"text": data.heading}

    @at(kind="card", style="bg-surface rounded-md")
    def revenue(self, data: KpiInput) -> dict:
        return {"title": "Revenue", "value": data.revenue}

    @at(kind="card", style="bg-surface rounded-md")
    def customers(self, data: KpiInput) -> dict:
        return {"title": "Customers", "value": data.customers}
```

Cells render in method-declaration order. Metadata stores the typed input (not
the expanded layout), so `doc get` round-trips the original JSON. Templates are
available through the Python API (`document.add_slide`), the Streamlit preview,
and the CLI:

```bash
uv run your-slides templates list --json
uv run your-slides templates inspect kpi-duo --json     # description + input JSON schema
uv run your-slides slide add deck.pptx --template kpi-duo \
  --data-json '{"heading": "Q3", "revenue": "$1.2M", "customers": "8,400"}'
```

> Free-form render-function templates (`def my_slide(slide, ctx, data)`) are
> still supported as a low-level escape hatch, but new templates should use the
> grid-composed class form above.

The Streamlit preview app auto-generates form fields from each registered template's model and auto-selects its `default_frame`.

### Adding a frame (in implementation package)

```python
from pptx.slide import Slide

from slides_factory.render_context import RenderContext
from your_impl.app import app
from your_impl.frame_solid import render_solid_frame
from your_impl.palettes import ON_LIGHT

@app.frame("my-frame", name="My Frame", palette=ON_LIGHT)
def my_frame(slide: Slide, ctx: RenderContext) -> None:
    render_solid_frame(slide, ctx, group="main", index=1)
```

## Implementation helpers

Template and frame render helpers (`set_title`, `fill_bullets`, `render_solid_frame`, etc.) belong in the **implementation package**, not core. A reference implementation may ship `templates/helpers/`, `render/solid.py`, and `render/image.py` alongside its frames.

## RTL

Templates position shapes in LTR coordinates; `RTLLayout` mirrors for RTL:

```
new_left = slide_width - left - width
```

Call `RTLLayout(ctx).position_for_reading(shape)` on placeholders and `RTLLayout(ctx).x(left, width)` on custom shapes.

## Catalog API

Prefer the `SlideFactory` instance (`app.list_templates()`, `app.get_template()`, …) inside implementation packages. Module-level helpers in `slides_factory.template` and `slides_factory.frame` delegate to `get_app()` for scripts and quick exploration.

## Template preview (Streamlit)

The core includes an optional Streamlit UI for visually testing templates in [`slides_factory/preview/`](slides-factory/slides_factory/preview/):

| Module | Role |
|--------|------|
| `preview/render.py` | Render one slide to `.pptx` bytes; convert to PNG |
| `preview/forms.py` | Auto-generate Streamlit fields from `TemplateInput` models |
| `preview/frames.py` | Resolve preview frame from template `default_frame` or brand fallback |
| `preview/app.py` | `run_preview_app(factory, …)` — reusable UI for implementations |

Install preview extras:

```bash
uv sync --extra preview   # from slides-factory/
```

Configure preview on the `SlideFactory` instance (`preview_impl_module`, `preview_brand`, `preview_page_title`), then launch via the CLI:

```bash
uv run your-slides preview
```

The UI builds form fields automatically from each template's `TemplateInput` model (text inputs, dynamic lists with **+ Add**, nested object repeaters).

### LibreOffice (PNG preview)

In-browser PNG previews use LibreOffice’s headless `soffice` CLI to convert `.pptx` → PNG. Without LibreOffice, the app still renders slides and offers a `.pptx` download.

```bash
# macOS
brew install --cask libreoffice

# verify
soffice --version
```

The first conversion after install can take 30–45 seconds while LibreOffice starts.

## Dependencies

- `python-pptx`, `pydantic`, `pyyaml`, `fonttools`, `lxml`, `pillow`, `typer`
- `streamlit` (optional, `[preview]` extra)

## Tests

Core tests use an isolated `SlideFactory("test-core")` fixture — no implementation package is imported.

```bash
uv sync --group dev
./scripts/test.sh
# or: uv run pytest
```
