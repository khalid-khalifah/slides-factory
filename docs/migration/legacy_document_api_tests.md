# Legacy `document.*` grid API — failing test audit

After the `document.py` refactor (facade delegates to `slides_factory/core/`), the
following tests still called removed module-level helpers. This document records
each failure, whether equivalent behaviour exists in core, and what was done.

**Audit date:** 2026-06-17  
**Core replacement tests:** `tests/test_core_services.py`, `tests/test_theme_resolver.py`

---

## Summary

| Status | Count |
|--------|------:|
| Covered in core — legacy test removed (initial audit) | 4 |
| Previously flagged — now implemented in `GridSlideService` | 10 |
| **Current test files** | `test_grid_slides.py`, `test_core_services.py`, `test_cli_builder.py`, `test_frame_slide.py`, `test_manager.py` |

All gaps (GAP-01 through GAP-10) are implemented in `slides_factory/core/grid.py` and
exposed via thin `document.*` facade methods. **149 tests pass** as of this update.

---

## Covered in core (tests removed)

### 1. `test_new_grid_slide_starts_empty`
- **File:** `tests/test_cli_builder.py`
- **Legacy API:** `document.new_grid_slide(prs, grid=...)`
- **Core equivalent:** `LayoutEngine.resolve_blank_layout()` + `prepare_render()` + `render_frame()` + `render_grid()` + `write_metadata("$grid", ...)`
- **Core test:** `test_core_grid_lifecycle` step 1
- **Action:** Removed legacy test

### 2. `test_set_slide_updates_grid_and_info`
- **File:** `tests/test_cli_builder.py`
- **Legacy API:** `document.set_slide(prs, index, grid=..., frame_info=...)`
- **Core equivalent:** Mutate spec dict → `SlideManager.clear_slide_shapes()` → re-render frame + grid → `write_metadata`
- **Core test:** `test_core_grid_lifecycle` step 3 (grid class update)
- **Note:** `frame_info` merge semantics are not asserted in core yet (see gaps below)
- **Action:** Removed legacy test

### 3. `test_layout_blocked_on_no_playground_frame`
- **File:** `tests/test_frame_slide.py`
- **Legacy API:** `document.add_layout_slide(..., frame="cover")` should raise
- **Core equivalent:** `LayoutEngine.ensure_frame_allows_layout(frame_tpl)`
- **Core test:** `test_layout_engine_ensure_allows_layout`
- **Action:** Removed legacy test

### 4. `test_add_set_remove_cell_round_trip` (partial)
- **File:** `tests/test_cli_builder.py`
- **Legacy API:** `document.add_cell` append path
- **Core equivalent:** Append to `spec["cells"]` → clear → re-render
- **Core test:** `test_core_grid_lifecycle` step 2
- **Action:** Removed legacy test (see gaps for `set_cell` / `remove_cell`)

---

## Not covered in core (flagged — legacy tests removed)

> **Update:** All items below are now implemented. See `slides_factory/core/grid.py`
> and `tests/test_grid_slides.py`.

### GAP-01: `document.set_cell` — update one cell in place
- **Was tested by:** `test_add_set_remove_cell_round_trip`
- **Expected behaviour:** Update kind/at/props/style for cell `N` without replacing the whole spec
- **Core today:** None — callers must mutate `spec["cells"][N]` manually
- **Suggested home:** `LayoutEngine` helper or thin facade method calling re-render

### GAP-02: `document.remove_cell` — drop one cell
- **Was tested by:** `test_add_set_remove_cell_round_trip`
- **Expected behaviour:** `cells.pop(N)` then re-render
- **Core today:** None

### GAP-03: Element kind validation on append
- **Was tested by:** `test_add_cell_rejects_unknown_kind`
- **Expected behaviour:** `KeyError` when `kind` is not registered
- **Core today:** `Layout.from_spec` accepts any kind string; failure happens at render time

### GAP-04: Grid-slide guard for cell edits
- **Was tested by:** `test_add_cell_requires_grid_slide`
- **Expected behaviour:** `ValueError` when slide metadata is not `$grid`
- **Core today:** None — no `_require_grid_data` equivalent

### GAP-05: CLI `slide new` → core grid creation
- **Was tested by:** `test_cli_build_deck_round_trip`, `test_cli_slide_new_uses_set_for_frame_info`
- **Expected behaviour:** `mim-slides slide new` creates `$grid` slide via document API
- **Core today:** `cli.py` still calls `document.new_grid_slide` (missing)
- **Fix:** Wire CLI to `LayoutEngine` + `SlideManager` or restore facade

### GAP-06: CLI `el add` with repeated `--set` list props
- **Was tested by:** `test_cli_repeated_set_builds_list`
- **Depends on:** GAP-05 + GAP-01 append path
- **Core today:** Prop list building works in CLI; slide creation does not

### GAP-07: `add_layout_slide` save/reopen round-trip
- **Was tested by:** `test_layout_slide_round_trip_without_brand`
- **Expected behaviour:** Full layout spec persists; shapes render after `save_document` / `open_document`
- **Core today:** In-memory metadata round-trip only in `test_core_grid_lifecycle`

### GAP-08: Branded frame info layer on grid slides
- **Was tested by:** `test_layout_slide_with_frame_draws_info_layer`
- **Expected behaviour:** `frame_info` (e.g. title) renders when `frame="paneled"`
- **Core today:** `render_frame` exists but no integrated `add_layout_slide` path with brand

### GAP-09: Playground geometry for framed grids
- **Was tested by:** `test_layout_cells_land_inside_frame_playground`
- **Expected behaviour:** Card EMU box aligns with frame `playground` percent box
- **Core today:** `prepare_render` attaches playground to ctx; no assertion test

### GAP-10: `set_slide` frame_info merge
- **Was tested by:** `test_set_slide_updates_grid_and_info` (frame_info half)
- **Expected behaviour:** Merge new frame_info keys onto existing spec
- **Core today:** Only full spec replacement in lifecycle test

---

## Core API reference (replacement patterns)

```python
from slides_factory.core.engine import LayoutEngine
from slides_factory.core.manager import SlideManager
from slides_factory.layout_spec import Layout
from slides_factory.metadata import write_metadata, read_metadata

engine = LayoutEngine(prs)
mgr = SlideManager(prs)

# New grid slide
slide = prs.slides.add_slide(engine.resolve_blank_layout())
spec = {"grid": "grid-cols-2", "cells": [], "frame_info": {}, "frame_style": {}}
ctx, frame_tpl, _, brand, _, _ = engine.prepare_render(frame=None, rtl=False, locale="en")
engine.render_frame(slide, frame_tpl, ctx, brand, spec["frame_info"], spec.get("frame_style"))
engine.render_grid(slide, Layout.from_spec(spec), ctx)
write_metadata(slide, "$grid", spec)

# Append cell + re-render
spec["cells"].append({"at": "", "element": {"kind": "text", "props": {"text": "Hi"}, "style": {}}})
mgr.clear_slide_shapes(slide)
engine.render_frame(slide, frame_tpl, ctx, brand, spec["frame_info"], spec.get("frame_style"))
engine.render_grid(slide, Layout.from_spec(spec), ctx)
write_metadata(slide, "$grid", spec)

# Block layout on cover frame
engine.ensure_frame_allows_layout(get_frame("cover"))  # raises ValueError
```

---

## Next steps (completed)

1. ~~Wire `cli.py` grid commands to core~~ — `document` facade delegates to `GridSlideService`
2. ~~Add `GridSlideService` for cell CRUD + guards~~ — `slides_factory/core/grid.py`
3. ~~Add core integration tests for branded layout + playground bounds~~ — `tests/test_grid_slides.py`
