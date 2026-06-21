# Run 4 — Color System Consolidation

**Effort:** ~1 hour  
**Risk:** Low (cleaning up already-working code, consolidating not rewriting)  
**Impact:** Medium (eliminates confusion between two resolution paths)
**Status:** ✅ **DONE** — committed `fac1952`, pushed to `main`

---

## Goal

After Run 1 deleted the dead `core/resolver.py` + `core/tokens.py`, this run
ensures the remaining color resolution system is clean, well-documented, and
doesn't have leftover references to the deleted modules.

---

## The Current (Live) System

The production color resolution happens in **two modules**:

### `styling/theme.py` — the "theme scale" analog

Provides:
- `SPACING_SCALE`, `FONT_SIZES_PT`, `RADIUS_SCALE` — numeric scales
- `resolve_color_token(token, palette)` — maps palette tokens (`primary`, `muted`, `highlight`, `main`, `surface`) to `#RRGGBB` strings using `SlidePalette`
- `resolve_style_color(ref, ctx)` — the main entry point; resolves palette tokens AND brand refs (`main:0`, `on-main:0`)
- `resolve_style_contrast(ref, ctx)` — resolves contrast colors for text/icons on brand surfaces

### `styling/models.py` — brand color reference helpers

Provides:
- `is_brand_fill_ref(ref)` — checks if a string is `{group}:{index}` format
- `is_brand_contrast_ref(ref)` — checks if a string is `on-{group}:{index}` format
- `resolve_brand_color(brand, ref)` — resolves `main:0` → `#RRGGBB`
- `resolve_brand_contrast_ref(brand, ref)` — resolves `on-main:0` → `#RRGGBB`

### `palette.py` — the palette abstraction

Provides:
- `SlidePalette` — dataclass for text/highlight/main/extras
- `palette_from_brand_surface()` — constructs a `SlidePalette` from `BrandTheme`

---

## Issues to Fix

### Issue 1: `COLOR_TOKENS` is unused

`styling/theme.py` defines `COLOR_TOKENS: frozenset[str]` from `_FALLBACK_COLORS.keys()`.
It is never referenced anywhere.

**Action:** Delete `COLOR_TOKENS`. Keep `_FALLBACK_COLORS`.

---

### Issue 2: `resolve_style_contrast()` is unused in render code

`styling/theme.py:resolve_style_contrast()` is defined but not called by any
element render function (`card.py`, `text.py`). Those render functions call
`resolve_style_color()` directly.

**Verification:**
```bash
grep -rn "resolve_style_contrast" slides_factory/ --include="*.py"
```

If only `styling/theme.py` defines it and nothing calls it, consider deleting
it or marking it as part of the public API with a docstring explaining when to
use it instead of `resolve_style_color()`.

---

### Issue 3: `resolve_brand_color()` and `resolve_brand_contrast_ref()` are tangled imports

`styling/theme.py` imports `resolve_brand_color` and `resolve_brand_contrast_ref`
from `styling.models.py` at function-call time (inside `resolve_style_color` and
`resolve_style_contrast`). This is fine for avoiding circular imports, but it
means the import happens on every color resolution. Since these are small
functions, this is a micro-optimization — but it's worth documenting why these
imports are lazy.

**Action:** Add a comment in `resolve_style_color()`:
```python
# Lazy import to break circular dependency: styling.models imports from styling.theme
```

Or better: move the brand color resolution into `brand/theme.py` where it
conceptually belongs — it operates on `BrandTheme`, not on styling concepts.

---

### Issue 4: `hex_to_rgb()` should be consolidated

After Run 3 moved `hex_to_rgb()` to `color_utils.py`, ensure ALL callers import
from `color_utils`:

- `palette.py:apply_paragraph_color()` uses `from slides_factory.brand import hex_to_rgb`
  → Change to `from slides_factory.color_utils import hex_to_rgb`
- `elements/card.py:render_card()` uses `from slides_factory.brand import hex_to_rgb`
  → Change to `from slides_factory.color_utils import hex_to_rgb`
- `elements/base.py:style_paragraph()` uses `from slides_factory.brand import hex_to_rgb`
  → Change to `from slides_factory.color_utils import hex_to_rgb`

---

## Step-by-Step Actions

### Step 1: Delete `COLOR_TOKENS` from `styling/theme.py`

Remove line ~69:
```python
COLOR_TOKENS: frozenset[str] = frozenset(_FALLBACK_COLORS)
```

### Step 2: Audit `resolve_style_contrast()` usage

```bash
grep -rn "resolve_style_contrast" slides_factory/ tests/ --include="*.py"
```

If it has production callers, keep it and add a docstring. If only tests call
it, keep it but move to a utils module.

### Step 3: Move brand color resolution to `brand/theme.py`

Currently `resolve_brand_color()` and `resolve_brand_contrast_ref()` live in
`styling/models.py`. They operate on `BrandTheme`, not on styling concepts.
Moving them to `brand/theme.py` eliminates the cross-package import between
`styling/` and `brand/`.

```python
# New functions in brand/theme.py
def resolve_brand_color(brand: BrandTheme, ref: str) -> str:
    """Resolve a brand fill reference like 'main:0' to a #RRGGBB color."""
    group, index_text = ref.split(":", 1)
    return resolve_color(brand, group, int(index_text))

def resolve_brand_contrast_ref(brand: BrandTheme, ref: str) -> str:
    """Resolve 'on-main:0' to the contrast color for readability on that fill."""
    group, index_text = ref.removeprefix("on-").split(":", 1)
    return resolve_contrast(brand, group, int(index_text))
```

Then update `styling/models.py` to import these from `brand.theme` instead of
defining them locally. Or better: remove them from `styling/models.py` entirely
and have `styling/theme.py:resolve_style_color()` import from `brand.theme`.

### Step 4: Document the color resolution architecture

Add a module-level docstring to `styling/theme.py` that explains the resolution
path:

```python
"""
Color resolution pipeline:

1. Brand fill refs ("main:0") → BrandTheme.colors → resolve_color()
2. Brand contrast refs ("on-main:0") → BrandTheme.colors → resolve_contrast()
3. Palette tokens ("primary", "surface", "muted", "highlight")
   → SlidePalette from frame → resolve_color_token()
4. Neutral fallbacks (when no brand/palette) → _FALLBACK_COLORS

Entry point: resolve_style_color(ref, ctx)
"""
```

---

## Acceptance Criteria

- [x] `COLOR_TOKENS` variable removed from `styling/theme.py`
- [x] `resolve_style_contrast()` usage is audited and documented (kept for external consumers, added docstring)
- [x] Brand color resolution functions live in `brand/theme.py`, not `styling/models.py` (re-exported from `styling.models` for backward compat)
- [x] All `hex_to_rgb()` imports go through `color_utils.py` (already done in Run 3)
- [x] `styling/theme.py` has a module-level docstring explaining the resolution pipeline
- [x] All tests pass (145/145)
