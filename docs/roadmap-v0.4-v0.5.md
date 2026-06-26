# Slides Factory — v0.4 & v0.5 Roadmap

**Date:** 2026-06-26  
**Branch:** `slides-factory` core library  
**Depends on:** v0.3 (complete)

---

## Summary

Two waves building on the v0.3 foundation (image, rich-text, auto-rows, data-driven slides):

| Wave | Features | Total Effort |
|------|----------|-------------|
| **v0.4** | Brand inheritance, table element, layout debug mode | ~5–8 hours |
| **v0.5** | Headless PNG export, template composition | ~8–11 hours |

---

## v0.4 — Brand Inheritance, Tables, Debug Mode

### Feature 4.1 — Brand Theme Inheritance

**Priority:** High | **Effort:** 1–1.5 hours | **Independent:** Yes

#### Why

Brand YAML files duplicate shared settings (page size, layout percentages, basic color pairs). Inheritance lets a child brand override only what differs from a parent.

#### What to build

A new `extends` key in brand YAML:

```yaml
# child-brand.yaml
extends: base-brand.yaml
colors:
  main:
    - color: "#CUSTOM"
      contrast: "#FFFFFF"
  # secondary and basic are inherited from parent
```

**Merge rules:**
- `name` — child overrides parent (or defaults to parent name + variant)
- `default_frame`, `base_pptx`, `lock_frame_shapes` — child value wins if present, else parent
- `page` — child overrides parent entirely (field-level merge is confusing)
- `layout.logos` — deep-merge: child locale entries override parent locale entries
- `layout.elements` — shallow merge: child entries override parent by key
- `colors.main`, `colors.secondary`, `colors.basic` — child **replaces** parent list (not appends)
- `fonts.slots` — child overrides parent by slot key
- `logos` — child overrides parent by logo key

#### Implementation

Extend `load_brand()`:

```python
def load_brand(path: Path) -> BrandTheme:
    source = path.resolve()
    raw = _read_yaml(source)
    # ... existing validation ...

    parent_raw = None
    if "extends" in raw:
        parent_path = source.parent / raw["extends"]
        parent_raw = _read_yaml(parent_path)
        raw = _merge_brand_dicts(parent_raw, raw)

    # ... rest of existing load logic ...


def _merge_brand_dicts(parent: dict, child: dict) -> dict:
    """Deep merge: child values override parent; lists replace, not append."""
    merged = dict(parent)
    for key, value in child.items():
        if key == "extends":
            continue  # already resolved
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_brand_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged
```

**Edge cases:**
- Circular inheritance (`a → b → a`) → `SlidesFactoryError` with chain trace
- Missing parent file → `FileNotFoundError` with resolved path
- Chains deeper than 5 → warning (likely a mistake)

#### Tests

- `test_extends_page_size` — child overrides page dimensions
- `test_extends_colors_replace` — child overrides only `main`, inherits `secondary`
- `test_extends_fonts_merge` — child overrides `title` font, inherits `body`
- `test_extends_logos_merge` — child adds a logo, inherits others
- `test_circular_inheritance_raises` — a→b→a chain
- `test_missing_parent_raises` — parent file not found

#### Files

| File | Change |
|------|--------|
| `slides_factory/brand/theme.py` | `load_brand()` extended with `extends` resolution |
| `tests/test_brand.py` | Add inheritance tests |

---

### Feature 4.2 — Table Element

**Priority:** High | **Effort:** 3–4 hours | **Independent:** Yes

#### Why

Data-heavy presentations (financial reports, dashboards, comparisons) need structured tables. python-pptx has native `slide.shapes.add_table()` — the missing piece is a styling system that maps theme tokens to OOXML table properties.

#### What to build

New `@app.element("table", ...)` in `slides_factory/elements/table.py`:

**Props model:**
```python
class TableRow(BaseModel):
    cells: list[str]


class TableProps(BaseModel):
    """Content props for the table element."""
    headers: list[str] = []
    rows: list[TableRow]
    col_widths: list[float] | None = Field(
        default=None,
        description="Relative column widths (e.g. [2, 1, 1]). If unset, equal distribution."
    )
```

**Style model:**
```python
class TableStyle(BaseModel):
    """Look overrides for the table element."""
    header_color: str = Field(
        default="surface",
        description="Palette token or brand fill reference for header row."
    )
    header_text_color: str = Field(
        default="primary",
        description="Text color for header cells."
    )
    stripe_color: str | None = Field(
        default=None,
        description="Palette token for alternating row background (None = no striping)."
    )
    grid_color: str | None = Field(
        default=None,
        description="Border color hex. None = no borders."
    )
    font: str = Field(default="body")
    text_size: str = Field(default="sm")
    header_bold: bool = True
```

**Render behavior:**
1. Build `col_widths` from `props.col_widths` if given, else distribute equally
2. Create table via `slide.shapes.add_table(rows=1+len(rows), cols=len(headers), ...)`
3. Set column widths proportionally to `box.width`
4. Header row: fill with `header_color`, bold text, `header_text_color`
5. Data rows: alternating `stripe_color` when set
6. Grid lines: `grid_color` when set, applied per-cell via OOXML `<a:ln>` elements
7. Apply font via `apply_shape_font()` on the table shape

**Fit behavior:** If the table overflows the cell box vertically, rows should auto-size (python-pptx default). Column widths are proportional to `box.width`.

#### CLI

```bash
your-slides el add deck.pptx --index 0 --kind table \
  --set headers='["Q1","Q2","Q3","Q4"]' \
  --set rows='[{"cells":["$100","$200","$300","$400"]},{"cells":["$150","$250","$350","$450"]}]'
```

JSON auto-parsing (already implemented in v0.3) handles the `headers` and `rows` values.

#### Tests

- `test_table_basic` — headers + 2 rows, columns equally distributed
- `test_table_col_widths` — custom column widths applied proportionally
- `test_table_no_headers` — empty headers list, only data rows
- `test_table_striping` — alternating row background when `stripe_color` set
- `test_table_grid` — borders visible when `grid_color` set
- `test_table_empty` — empty headers + empty rows → empty table shape
- `test_table_cli` — element registered, props validate

#### Files

| File | Change |
|------|--------|
| `slides_factory/elements/table.py` | **New** — props, style, render function |
| `slides_factory/app.py` | Register `"table"` in `_register_builtins()` |
| `tests/test_elements.py` | Add table element tests (or new `test_table.py`) |

---

### Feature 4.3 — Layout Debug Mode

**Priority:** Medium | **Effort:** 1–2 hours | **Independent:** Yes

#### Why

Debugging grid layouts by trial-and-error is slow. A `--debug` flag that renders grid lines, cell boundaries, padding regions, and cell indices turns the visual guesswork into a 2-second feedback loop.

#### What to build

A `--debug` flag on `slide new` and `slide add` that adds diagnostic shapes before normal rendering:

```bash
your-slides slide new deck.pptx --grid "grid-cols-[2_1] grid-rows-2 gap-4" --debug
```

**Rendered diagnostics (low opacity, behind content):**

1. **Playground boundary** — dashed red rectangle showing the body region
2. **Grid lines** — dashed gray lines showing column/row boundaries
3. **Padding region** — semi-transparent fill between playground edge and inner grid
4. **Gap regions** — lighter semi-transparent bands between tracks
5. **Cell boundaries** — thin solid blue/red rectangles around each cell
6. **Cell labels** — small text `[0,0]`, `[0,1]`, … in the top-left corner of each cell

All diagnostic shapes are rendered **before** the actual content so they appear behind it.

#### Implementation

```python
class LayoutEngine:
    def render_debug_layer(self, slide, layout, ctx):
        """Render diagnostic shapes for a layout (grid lines, cell labels, etc.)."""
        ...
    
    def render_grid(self, slide, layout, ctx, *, debug=False):
        if debug:
            self.render_debug_layer(slide, layout, ctx)
        render_layout(slide, layout, ctx, app=self.app)
```

The `debug_grid` is a separate CSS-like class alongside `grid`:

```python
# CLI
your-slides slide new deck.pptx --debug --grid "..."

# Python API  
document.new_grid_slide(prs, ..., debug=True)
```

Alternatively, store a `debug: bool` flag in the layout metadata so `get_slide_info()` reports it.

**Simpler alternative:** Add `--debug` only to the CLI and render debug shapes directly in the `slide new` / `el add` command handlers before calling the normal render path. This avoids touching the core engine.

#### Tests

- `test_debug_playground_visible` — playground boundary shape present
- `test_debug_cell_labels` — cell index text shapes present
- `test_debug_grid_lines` — column/row boundary shapes present
- `test_debug_behind_content` — debug shapes have lower z-order than content

#### Files

| File | Change |
|------|--------|
| `slides_factory/layout/debug.py` | **New** — `render_debug_layer()` |
| `slides_factory/core/engine.py` | Optional debug pass before `render_grid()` |
| `slides_factory/cli.py` | `--debug` flag on `slide new` / `slide add` |
| `tests/test_debug_layout.py` | **New** — debug rendering tests |

---

## v0.5 — Headless PNG Export, Template Composition

### Feature 5.1 — Headless PNG Export

**Priority:** High | **Effort:** 4–6 hours | **Independent:** Yes

#### Why

Currently preview uses LibreOffice (`soffice`) which requires a 500MB+ installation. A pure-Python PNG renderer lets server-side pipelines (CI, headless Docker, Lambda) generate slide previews without external dependencies.

#### Approach

Two-tier strategy:

**Tier 1 — LibreOffice (fast path, if installed):**
Use existing `preview/render.py` → `pptx_bytes_to_pngs()`. No changes needed.

**Tier 2 — Pillow renderer (fallback, always available):**
A new `slides_factory/export/pillow_render.py` that rasterizes a slide by drawing shapes pixel-by-pixel:

1. Read EMU dimensions from `ctx.slide_width` / `ctx.slide_height`
2. Calculate DPI → pixel dimensions (target: 150 DPI for preview quality)
3. Create a `PIL.Image.new("RGB", ...)` canvas with white background
4. Walk shapes on the slide:
   - **Auto shapes** (rectangles, rounded rectangles) → `ImageDraw.rounded_rectangle()`
   - **Text boxes** — measure text with `PIL.ImageFont`, draw at coordinates
   - **Pictures** — open image, resize to fit box, paste onto canvas
   - **Placeholders** — skip (they're already rendered as concrete shapes by python-pptx)
5. Return `bytes` (PNG format)

**API:**
```python
# slides_factory/export/__init__.py
def slide_to_png_bytes(slide, *, dpi: int = 150) -> bytes:
    """Render one slide to PNG bytes using Pillow (no LibreOffice needed)."""
    ...

def slide_to_png_file(slide, path: Path, *, dpi: int = 150) -> None:
    """Render one slide to PNG and save to *path*."""
    ...

def export_all_slides(prs, output_dir: Path, *, dpi: int = 150) -> list[Path]:
    """Render all slides to PNG files. Returns list of output paths."""
    ...

def pptx_bytes_to_pngs(pptx_bytes: bytes, *, dpi: int = 150) -> list[bytes]:
    """Render a .pptx to PNGs. Uses LibreOffice if installed, else Pillow fallback."""
    ...
```

**Scope:** Start with auto-shapes + text — cover the `text`, `card`, and `image` elements. Tables (v0.4) and custom frames come later. The renderer should raise `NotImplementedError` for unsupported shape types, not silently skip them.

**DPI table:**

| DPI | 16:9 (13.333" × 7.5") | 4:3 (10" × 7.5") |
|-----|------------------------|-------------------|
| 72  | 960 × 540 | 720 × 540 |
| 150 | 2000 × 1125 | 1500 × 1125 |
| 300 | 4000 × 2250 | 3000 × 2250 |

Default 150 DPI for preview; 300 DPI for export.

#### Tests

- `test_pillow_render_text_slide` — text-only slide → correct PNG dimensions, readable text
- `test_pillow_render_card_slide` — card element → filled rounded rect + text
- `test_pillow_render_image_slide` — image element → picture at correct position
- `test_pillow_render_grid_slide` — grid with multiple elements → all rendered
- `test_pillow_render_dpi_150` — verify output pixel dimensions match DPI
- `test_pillow_render_unknown_shape` — unsupported shape → `NotImplementedError`
- `test_pillow_fallback_when_no_soffice` — auto-falls back when LibreOffice missing
- `test_pillow_export_all_slides` — multi-slide export creates correct file count

#### Files

| File | Change |
|------|--------|
| `slides_factory/export/__init__.py` | **New** — public API |
| `slides_factory/export/pillow_render.py` | **New** — Pillow-based rasterizer |
| `slides_factory/export/shapes.py` | **New** — per-shape-type drawing functions |
| `slides_factory/preview/render.py` | Update `pptx_bytes_to_pngs()` to try Pillow fallback |
| `tests/test_pillow_export.py` | **New** — export tests |

---

### Feature 5.2 — Template Composition

**Priority:** Medium | **Effort:** 4–5 hours | **Independent:** No (touches template system)

#### Why

Common slide patterns like "hero heading + 3 KPI cards" or "title + 2-column comparison" are compositions of simpler templates. Without composition, users copy-paste `@at` methods or duplicate entire template classes.

#### What to build

Allow `@at` methods to delegate to another template instead of an element:

```python
@app.template("hero-kpi", name="Hero + KPIs",
              grid="grid-cols-1 grid-rows-[1_3] gap-4")
class HeroKpi(Template):
    @at("col-span-1", template="hero-heading")
    def heading(self): ...
    
    @at("col-span-1", template="kpi-row")
    def metrics(self): ...
```

**Input JSON:**
```json
{
  "heading": {"title": "Q3 Review", "subtitle": "Key Results"},
  "metrics": {"revenue": {"title": "Revenue", "value": "$1.2M"}, ...}
}
```

#### Changes needed

1. **`CellDef`** (`templating.py`): add `template: str | None` field alongside `kind`
2. **`at()` decorator**: accept `template=` kwarg mutually exclusive with `kind=`
3. **`input_model_from_template()`** (`registration.py`): when `cell.template` is set, resolve the sub-template's input model via `factory.get_template(cell.template).input_model` and use it as the nested field type
4. **`Template.build()`** (`templating.py`): when `cell.template` is set, call `sub_template.render(slide, cell_data, ctx)` instead of `element.render(slide, box, props, style, ctx)` — but use a **sub-region** approach: compute the cell's EMU box, create a sub-ctx with that box as the playground, and render the sub-template inside it
5. **`CellSpec`** (`layout_spec.py`): add `template: str | None` field

**Template rendering as sub-layout:**
```python
# In Template.build() — when rendering a composed cell:
if cell.template:
    sub_template = self._app.get_template(cell.template)
    sub_data = getattr(data, cell.name)  # the nested data for this sub-template
    sub_layout = sub_template.build(sub_data)
    # Render sub-layout in the cell's box
    render_layout(slide, sub_layout, cell_subctx, app=self._app)
else:
    # existing element render path
    element.render(slide, box, props, style, ctx)
```

**Constraints:**
- Sub-templates render inside their parent cell's EMU box (no grid interference)
- Nested composition (template → template → template) works recursively
- Circular references detected at registration time (during `input_model_from_template`)
- The composed template's `default_frame` is ignored; the parent's frame controls the slide

#### Tests

- `test_compose_two_templates` — parent with 2 sub-template cells renders both
- `test_compose_nested` — 3-level deep composition
- `test_compose_inline_with_elements` — mixed: one cell uses `template=`, another uses `kind=`
- `test_circular_composition_raises` — template A composes B which composes A → error at registration
- `test_compose_cli` — `slide add` with composed template works

#### Files

| File | Change |
|------|--------|
| `slides_factory/templating.py` | `CellDef` gets `template`, `at()` gets `template=`, `build()` delegates to sub-template |
| `slides_factory/layout_spec.py` | `CellSpec` gets `template` field |
| `slides_factory/registration.py` | `input_model_from_template()` resolves sub-template models |
| `tests/test_composition.py` | **New** — composition tests |

---

## Execution Plan

### v0.4 — parallel execution possible

```
Feature 4.1 (brand inheritance) ───── independent
Feature 4.2 (table element)    ───── independent  
Feature 4.3 (debug mode)       ───── independent
```

All three can be developed in parallel or any order. No dependencies between them or on v0.3 features.

### v0.5 — sequential preferred

```
Feature 5.1 (PNG export)  ───── independent (can start anytime)
Feature 5.2 (composition) ───── depends on v0.3 template system + v0.4 registration model
```

Feature 5.1 can start in parallel with v0.4 work. Feature 5.2 touches the template infrastructure heavily — best done after v0.4 is stable.

### Recommended schedule

| Step | Duration | Accumulated |
|------|----------|-------------|
| 4.1 Brand inheritance | 1–1.5h | 1.5h |
| 4.2 Table element | 3–4h | 5.5h |
| 4.3 Debug mode | 1–2h | 7.5h |
| **v0.4 total** | **5–8h** | |
| 5.1 PNG export | 4–6h | 13.5h |
| 5.2 Template composition | 4–5h | 18.5h |
| **v0.5 total** | **8–11h** | |

---

## Acceptance Criteria

### v0.4

1. **Brand inheritance:** `child.yaml` with `extends: parent.yaml` resolves correctly. Merged colors, fonts, and logos match merge rules. Circular chains raise clear errors.

2. **Table element:** `el add --kind table --set headers='["A","B"]' --set rows='[...]'` renders a styled table with header fill, alternating rows, and proportional columns.

3. **Debug mode:** `slide new --grid "..." --debug` renders grid lines, cell labels, and playground boundary behind content. Debug shapes don't appear in normal (non-debug) slides.

4. **Tests:** `uv run pytest` — zero regressions. Ruff clean.

### v0.5

5. **PNG export:** `export_all_slides(prs, tmp_path)` produces one PNG per slide at 150 DPI. Text, cards, and images render visibly. Falls back to Pillow when LibreOffice unavailable. LibreOffice path unchanged.

6. **Template composition:** A template referencing sub-templates via `template=` renders correctly. Nested composition works. Circular composition detected and rejected at registration time.

7. **Tests:** `uv run pytest` — zero regressions. Ruff clean.
