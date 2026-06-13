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
  → frame.render(slide, ctx)       # background + logo
  → template.render(slide, data, ctx)
  → metadata.write_metadata()
  → save_document()                 # embeds fonts
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

```python
from typing import Annotated

from pydantic import Field
from pptx.slide import Slide

from slides_factory.render_context import RenderContext
from slides_factory.template_input import TemplateInput
from your_impl.app import app
from your_impl.helpers import extract_title, set_title

class MySlideInput(TemplateInput):
    title: Annotated[str, Field(description="Slide title")]

def _extract_my_slide(slide: Slide):
    return {"title": extract_title(slide)}

@app.template(
    "my-slide",
    name="My Slide",
    layout_name="Title and Content",
    tags=["content", "list"],
    default_frame="my-frame",  # optional — used when --frame is omitted
    extract=_extract_my_slide,
)
def my_slide(slide: Slide, ctx: RenderContext, data: MySlideInput) -> None:
    set_title(slide, data.title, ctx)
```

Each template declares exactly one `TemplateInput` subclass as its `data` parameter. Optional `default_frame` on `@app.template` picks the page shell when `--frame` is omitted (overrides brand YAML `default_frame`). Optional `tags` help navigate the catalog in the CLI:

```bash
uv run your-slides templates list          # includes default_frame per template
uv run your-slides templates list --tag content
uv run your-slides templates inspect my-slide --json
uv run your-slides templates tags
```

The Streamlit preview app auto-generates form fields from that model and auto-selects each template's `default_frame` when you switch templates.

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
