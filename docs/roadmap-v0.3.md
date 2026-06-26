# Slides Factory — v0.3 Roadmap

**Date:** 2026-06-26  
**Status:** Planned  
**Branch:** `slides-factory` core library

---

## Summary

Implement four high-impact features to take the library from "solid engine, thin vocabulary" to "usable for real presentations without escape hatches":

| # | Feature | Priority | Estimated Effort |
|---|---------|----------|-----------------|
| 1 | Image/picture element | 🔴 Critical | 1–2 hours |
| 2 | Data-driven slide generation (`for_each`) | 🔴 Critical | 3–4 hours |
| 3 | Grid auto-rows (`grid-rows-auto`) | 🟡 High | 1 hour |
| 4 | Rich text / inline formatting in text element | 🟡 High | 2 hours |

**Total:** ~7–9 hours

---

## Feature 1: Image Element

### Why

Every presentation framework needs images. Currently only `text` and `card` elements exist. Private helpers `resolve_raster_logo()` in `brand/logos.py` and `image_aspect_ratio()` in `layout/pct.py` already handle SVG→PNG conversion and aspect-ratio math — most of the plumbing is in place.

### What to build

A new `@app.element("image", ...)` in `slides_factory/elements/image.py`:

**Props model:**
```python
class ImageProps(BaseModel):
    src: Path | str
    alt: str = ""
    fit: Literal["contain", "cover", "stretch", "fill"] = "contain"
```

**Style model:**
```python
class ImageStyle(BaseModel):
    radius: str = Field(default="none", description="Theme radius token.")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="0–1 opacity.")
```

**Render function:** `render_image(slide, box, props, style, ctx)` — opens the image with Pillow, computes placement based on `fit` mode within `box`, adds via `slide.shapes.add_picture()`, applies `radius` via rounded-rectangle adjustments, sets `alt` text.

**Fit modes:**
- `contain` — scale to fit, preserving aspect ratio, centered (letterbox)
- `cover` — scale to fill, preserving aspect ratio, crop overflow (python-pptx `.crop_*`)
- `stretch` — scale non-uniformly to fill box exactly
- `fill` — alias for stretch (backward compatible name)

### Registration

In `app.py:_register_builtins()`:
```python
from slides_factory.elements.image import ImageProps, ImageStyle, render_image
self._elements["image"] = element_from_function(
    render_image, kind="image", props_model=ImageProps, style_model=ImageStyle
)
```

### Tests

- `test_image_contain` — landscape image in square cell, verify no distortion
- `test_image_cover` — portrait image in landscape cell, verify crop
- `test_image_stretch` — verify non-uniform scaling
- `test_image_svg_source` — SVG input, verify Pillow opens rasterized version
- `test_image_alt_text` — verify alt text is set on the shape
- `test_image_cli` — `el add --kind image --set src=img.png`

### Files to touch

| File | Change |
|------|--------|
| `slides_factory/elements/image.py` | **New** — props, style, render function |
| `slides_factory/app.py` | Register in `_register_builtins()` |
| `tests/test_elements.py` | Add image element tests |
| `tests/fixtures/` | Add `test_image.jpg` or `test_image.png` |

### Edge cases

- Missing file → `FileNotFoundError` with clear path in message
- Unsupported format → `ValueError` listing supported formats
- Zero-size image → `ValueError`
- `fit="cover"` with aspect ratio so extreme the visible region is < 1px → clamp
- Brand with no `logos` directory — resolve relative to brand YAML location

---

## Feature 2: Data-Driven Slide Generation

### Why

The most-requested workflow gap: "render the same template once for each row in my data." Currently every slide must be added individually via `document.add_slide()`.

### What to build

A `document.add_slides_from_rows()` function and CLI command `slide add-many`.

**Python API:**
```python
def add_slides_from_rows(
    prs: Presentation,
    template_id: str,
    rows: list[dict[str, Any]],
    *,
    app: SlideFactory,
    frame: str | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> list[dict[str, Any]]:
    """Render *template_id* once for each row dict, returning per-slide results."""
```

Each row dict is passed as template data — the same JSON structure `add_slide()` expects.

**CLI:**
```bash
your-slides slide add-many deck.pptx --template kpi-card \
  --rows '[{"revenue": "$1.2M", "customers": "8.4K"}, {"revenue": "$2.3M", "customers": "12K"}]'
```

Or from a JSON file:
```bash
your-slides slide add-many deck.pptx --template kpi-card --rows-file data.json
```

The `--rows` flag accepts inline JSON (useful for agents). The `--rows-file` flag reads from disk.

### Validation

Each row is validated against the template's `input_model` via `template.validate_data(row)`. A `--skip-invalid` flag controls whether invalid rows are skipped or cause a hard error.

### Tests

- `test_add_slides_from_rows_creates_correct_count` — 3 rows → 3 slides
- `test_add_slides_from_rows_validates_each_row` — invalid row raises `ValidationError`
- `test_add_slides_from_rows_skip_invalid` — `--skip-invalid` skips bad rows
- `test_add_slides_from_rows_empty_list` — empty rows list → no slides, no error
- `test_add_slides_from_rows_cli` — full CLI round-trip

### Files to touch

| File | Change |
|------|--------|
| `slides_factory/document.py` | Add `add_slides_from_rows()` |
| `slides_factory/cli.py` | Add `slide add-many` command |
| `tests/test_document.py` | Add batch generation tests |

---

## Feature 3: Grid Auto-Rows

### Why

Currently `grid-rows-N` requires declaring row count upfront. With auto-rows, a template with 3 cells and `grid-rows-auto` would create 3 rows automatically instead of failing or requiring a hard-coded count. This is essential for data-driven slides where the number of rows varies.

### What to build

Extend `parse_grid()` in `styling/tokens.py` to accept `grid-rows-auto`:

```python
@dataclass(frozen=True)
class GridStyle:
    columns: tuple[float, ...] = (1.0,)
    rows: tuple[float, ...] = (1.0,)
    auto_rows: bool = False  # NEW
    col_gap: float = 0.0
    row_gap: float = 0.0
    pad_x: float = 0.0
    pad_y: float = 0.0
```

When `auto_rows=True`, `compute_cells()` in `layout/grid.py` calculates `nrows` from `len(cells)` at layout time rather than from the grid spec. The row count becomes `ceil(len(cells) / ncols)` — cells auto-place using the existing row-major placement.

### Behavior

- `grid-rows-auto` with `grid-cols-2` and 5 cells → 3 rows (2+2+1)
- `grid-rows-auto` with `grid-cols-1` and 4 cells → 4 rows (stacked)
- `grid-rows-auto` with explicit `row-start-N` on any cell → the max row index determines minimum rows
- `grid-rows-N` with `grid-rows-auto` → error (mutually exclusive)

### Tests

- `test_auto_rows_grid_cells_2` — 2 cols, 4 cells → 2 rows
- `test_auto_rows_uneven` — 2 cols, 3 cells → 2 rows (2+1)
- `test_auto_rows_explicit_start` — cell with `row-start-4` → 4 rows minimum
- `test_auto_rows_mutual_exclusion` — both `grid-rows-N` and `grid-rows-auto` → error

### Files to touch

| File | Change |
|------|--------|
| `slides_factory/styling/tokens.py` | Add `auto_rows` to `GridStyle`, parse `grid-rows-auto` |
| `slides_factory/layout/grid.py` | `compute_cells()` uses `auto_rows` to calculate `nrows` |
| `tests/test_grid_layout.py` | Add auto-rows test cases |

---

## Feature 4: Rich Text / Inline Formatting

### Why

Currently `TextProps` is `{text: str, bullets: list[str]}` — no way to bold a word, color a number red, italicize a term, or add a hyperlink mid-paragraph. Financial slides need red/green numbers. Branded slides need colored terms. Presentation slides need clickable links.

### What to build

Extend the `text` element to accept rich runs while maintaining backward compatibility:

```python
class TextRun(BaseModel):
    """One formatted segment within a text paragraph."""
    text: str
    bold: bool = False
    italic: bool = False
    color: str | None = None     # palette token or #RRGGBB hex
    size_pt: float | None = None # override text_size for this run
    link: str | None = None      # hyperlink URL
    strikethrough: bool = False
    underline: bool = False


class TextProps(BaseModel):
    """Content props for the text element."""
    text: str = ""
    bullets: list[str] = []
    runs: list[TextRun] = []  # NEW — supersedes text when non-empty
```

**Resolution rule:** When `runs` is non-empty, it replaces `text`+`bullets`. When `runs` is empty, existing behavior applies. This is fully backward compatible.

### Render behavior

`render_text()` checks `props.runs`. If present, it creates one paragraph per run list entry (or all runs in one paragraph with multiple runs). Each run gets individual `font.bold`, `font.italic`, `font.color.rgb`, `font.size`, and optional `hyperlink.address`.

### CLI

```bash
your-slides el add deck.pptx --index 0 --kind text \
  --set text="Revenue: " --set bold=true \
  --set text="\$1.2M" --set bold=true --set color="accent"
```

The repeated `--set` pattern with `runs` requires a slight extension to `_build_model_data` to handle list-typed fields of Pydantic models. Alternatively, accept a `--runs-json` flag:

```bash
your-slides el add deck.pptx --index 0 --kind text \
  --runs-json '[{"text":"Revenue: ","bold":false},{"text":"$1.2M","bold":true,"color":"#22C55E"}]'
```

### Tests

- `test_rich_text_basic` — bold + italic runs in one paragraph
- `test_rich_text_colors` — per-run color tokens resolve against palette
- `test_rich_text_backward_compat` — old `text`+`bullets` still works
- `test_rich_text_hyperlink` — run with `link="https://..."` creates clickable link
- `test_rich_text_multi_run_paragraph` — multiple runs in one paragraph
- `test_rich_text_cli` — CLI round-trip with `--runs-json`

### Files to touch

| File | Change |
|------|--------|
| `slides_factory/elements/text.py` | Add `TextRun`, extend `TextProps`, update `render_text()` |
| `slides_factory/cli.py` | Add `--runs-json` flag to `el add` / `el set` |
| `tests/test_elements.py` | Add rich text tests |

---

## Execution Order

1. **Feature 3** (Grid auto-rows) — foundational, needed by Feature 2
2. **Feature 1** (Image element) — independent, can be done in parallel
3. **Feature 4** (Rich text) — independent, can be done in parallel
4. **Feature 2** (Data-driven slides) — depends on Feature 3

### Dependency graph

```
Feature 3 (auto-rows) ────► Feature 2 (data-driven slides)
Feature 1 (image)     ────  (independent)
Feature 4 (rich text) ────  (independent)
```

Features 1, 3, and 4 can be implemented in any order or in parallel. Feature 2 depends on Feature 3.

---

## Acceptance Criteria

After all four features:

1. **Image:** `el add --kind image --set src=chart.png` creates a correctly-placed image in a grid cell. All four fit modes work. SVG sources auto-convert. Alt text is set.

2. **Data-driven:** `slide add-many --template kpi-card --rows-file data.json` creates N slides from N rows. Invalid rows are caught and reported. Empty rows list is a no-op.

3. **Auto-rows:** `grid-rows-auto` with 5 cells in 2 columns creates a 3-row grid. Explicit `row-start` pins work. Combined with `grid-rows-N` raises a clear error.

4. **Rich text:** Bold, italic, colored, and linked runs render correctly. Old `text`+`bullets` API unchanged. CLI `--runs-json` round-trips.

5. **All tests pass:** `uv run pytest` — zero regressions, new tests cover all edge cases.

6. **Ruff clean:** `uv run ruff check slides_factory/ tests/` — no lint errors.
