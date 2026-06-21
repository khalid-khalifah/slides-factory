# Run 5 — Code Quality, Error Handling & Testing

**Effort:** ~2–3 hours  
**Risk:** Low (adding quality, not restructuring)  
**Impact:** High (improves debuggability, catches real bugs earlier)
**Status:** ✅ **DONE** — committed `c1ab36d`, pushed to `main`

---

## Goal

Improve type hints, error handling, and test coverage across the codebase.
Focus on changes that catch bugs at development time rather than runtime, and
add domain-specific error types instead of bare `ValueError`.

---

## Section A: Type Hints

### A1: Replace `Any` return type on `prepare_render()` with a NamedTuple

**Current:** `engine.py:prepare_render()` returns a bare 6-element tuple:
```python
def prepare_render(...) -> tuple[RenderContext, Any, str, BrandTheme | None, bool, str]:
    ...
    return ctx, frame_tpl, frame_id, brand, active_rtl, active_locale
```

**Fix:** Create a `@dataclass` or `NamedTuple`:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RenderPrep:
    ctx: RenderContext
    frame_tpl: FrameTemplate | None
    frame_id: str
    brand: BrandTheme | None
    rtl: bool
    locale: str
```

Then:
```python
def prepare_render(...) -> RenderPrep:
    ...
    return RenderPrep(ctx, frame_tpl, frame_id, brand, active_rtl, active_locale)
```

Update all callers (`document.py`, `core/grid.py`) to use `prep.ctx`,
`prep.frame_tpl`, etc. instead of tuple unpacking. This gives IDE autocomplete
and prevents off-by-one bugs.

### A2: Type `_UNSET` sentinel properly

**Current:** `grid.py` defines `_UNSET: Any = object()` and uses it across 6
function signatures with parameters like `kind: Any = _UNSET`.

**Fix:** Create a sentinel type that type checkers can understand:
```python
from typing import Literal

class _UnsetType:
    """Sentinel for unset optional parameters."""
    def __repr__(self) -> str:
        return "UNSET"

_UNSET = _UnsetType()

# Then in function signatures:
def set_cell(
    self, index: int, cell: int, *,
    kind: str | _UnsetType = _UNSET,
    at: str | _UnsetType = _UNSET,
    props: dict[str, Any] | _UnsetType = _UNSET,
    style: dict[str, Any] | _UnsetType = _UNSET,
) -> dict[str, Any]:
    ...
```

### A3: Fix `Any` annotations in `brand/theme.py:load_brand()`

```python
# Current:
def load_brand(path: Path) -> BrandTheme:
    ...
    base = raw.get("base_pptx")  # type: Any
    theme = BrandTheme(
        ...
        base_pptx=Path(base) if base else None,  # type error risk
        ...
    )
```

`base` is `Any` from the YAML parse, which means `Path(base)` passes type
checking. At runtime, if the YAML contains a number, `Path(123)` will fail with
a confusing error.

**Fix:** Extract and validate before constructing `BrandTheme`:
```python
base_raw = raw.get("base_pptx")
base_pptx: Path | None = None
if base_raw is not None:
    if not isinstance(base_raw, str):
        raise TypeError(f"base_pptx must be a string path, got {type(base_raw).__name__}")
    base_pptx = Path(base_raw)
```

---

## Section B: Error Handling

### B1: Create domain-specific exception classes

**Current:** The codebase raises bare `ValueError` everywhere:

| Location | Error | Should be |
|---|---|---|
| `engine.py:prepare_render()` | `ValueError("Cannot use --frame without a brand...")` | `BrandRequiredError` |
| `layout/grid.py:_tracks()` | `ValueError("grid gaps exceed...")` | `GridOverflowError` |
| `layout/grid.py:compute_cells()` | `ValueError(f"cell span {n}x{m} exceeds...")` | `GridOverflowError` |
| `styling/theme.py:resolve_style_color()` | `ValueError(f"brand color reference {ref!r} requires...")` | `BrandRequiredError` |
| `app.py:get_app()` | `RuntimeError("No slide factory app configured...")` | `AppNotConfiguredError` |

**Action:** Create `slides_factory/exceptions.py`:
```python
"""Domain-specific exception classes for slides-factory."""

class SlidesFactoryError(Exception):
    """Base exception for all slides-factory errors."""

class AppNotConfiguredError(SlidesFactoryError, RuntimeError):
    """Raised when no SlideFactory app is active."""

class BrandRequiredError(SlidesFactoryError, ValueError):
    """Raised when a brand theme is required but not present."""

class GridOverflowError(SlidesFactoryError, ValueError):
    """Raised when grid cells cannot fit within the available region."""

class UnknownElementError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered element kind."""

class UnknownTemplateError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered template id."""

class UnknownFrameError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered frame id."""

class FontEmbeddingError(SlidesFactoryError, RuntimeError):
    """Raised when font embedding fails for a .pptx file."""
```

Then update all `raise ValueError(...)` and `raise KeyError(...)` calls to use
the appropriate domain exception.

### B2: Stop swallowing exceptions in CLI commands

**Current:** Every CLI command wraps its body in:
```python
try:
    # ... do work ...
except Exception as exc:
    _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)
```

This catches `KeyboardInterrupt`, `SystemExit`, `MemoryError`, and programming
errors like `AttributeError`. A `TypeError` from a bug in the code is silently
converted to `{ "ok": false, "error": "'NoneType' object has no attribute 'x'" }`.

**Fix:** Use a more targeted except clause:
```python
except (SlidesFactoryError, ValueError, KeyError, IndexError, FileNotFoundError) as exc:
    _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)
```

Programming errors (`AttributeError`, `TypeError`, `NameError`) should
propagate and crash visibly.

### B3: Warn on metadata decode failure

**Current:** `metadata.py:read_metadata()` silently returns `None` for invalid
JSON in speaker notes:
```python
try:
    payload = json.loads(text)
except json.JSONDecodeError:
    return None  # ← Silent failure
```

**Fix:** Add a warning so users know their metadata is corrupted:
```python
import warnings
try:
    payload = json.loads(text)
except json.JSONDecodeError as exc:
    warnings.warn(f"Corrupted slide metadata on slide {slide.slide_id}: {exc}")
    return None
```

---

## Section C: Testing Gaps

### C1: Add import-chain smoke test

Create `tests/test_imports.py`:
```python
"""Verify every public module can be imported independently without side effects."""

import importlib
import pytest

PUBLIC_MODULES = [
    "slides_factory",
    "slides_factory.app",
    "slides_factory.document",
    "slides_factory.template",
    "slides_factory.frame",
    "slides_factory.palette",
    "slides_factory.render_context",
    "slides_factory.layout_spec",
    "slides_factory.models",
    "slides_factory.typing_utils",
    "slides_factory.templating",
    "slides_factory.template_input",
    "slides_factory.frame_info",
    "slides_factory.locale",
    "slides_factory.metadata",
    "slides_factory.registration",
    "slides_factory.layout.grid",
    "slides_factory.layout.render",
    "slides_factory.layout.pct",
    "slides_factory.layout.fonts",
    "slides_factory.layout.font_embed",
    "slides_factory.layout.locks",
    "slides_factory.layout.rtl",
    "slides_factory.layout.z_order",
    "slides_factory.elements.base",
    "slides_factory.elements.card",
    "slides_factory.elements.text",
    "slides_factory.styling.theme",
    "slides_factory.styling.tokens",
    "slides_factory.styling.models",
    "slides_factory.brand.theme",
    "slides_factory.brand.doc",
    "slides_factory.brand.logos",
    "slides_factory.core.engine",
    "slides_factory.core.manager",
    "slides_factory.core.session",
    "slides_factory.core.grid",
]

@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_module_imports_cleanly(module_name):
    """Each public module should import without errors."""
    importlib.import_module(module_name)
```

### C2: Add test for `ensure_default_theme()` idempotency

```python
def test_default_theme_idempotent(tmp_path):
    """Creating the default theme multiple times should not fail."""
    from slides_factory.document import ensure_default_theme
    path1 = ensure_default_theme()
    path2 = ensure_default_theme()
    assert path1 == path2
    assert path1.exists()
```

### C3: Add test for `read_metadata()` with corrupted notes

```python
def test_read_metadata_corrupt_json(slide_with_notes):
    """Corrupted JSON in speaker notes should return None, not crash."""
    slide_with_notes.notes_slide.notes_text_frame.text = "{invalid json!!!"
    result = read_metadata(slide_with_notes)
    assert result is None
```

### C4: Remove dead code test coverage expectation

After Run 1 deletes `test_theme_resolver.py`, ensure CI coverage thresholds
don't break. If using `pytest-cov` with a `--cov-fail-under` flag, the overall
coverage percentage may need adjustment (or the deleted file was inflating
coverage with dead code tests).

---

## Acceptance Criteria

- [x] `prepare_render()` returns a `@dataclass` instead of a bare tuple (`RenderPrep` in `core/engine.py`)
- [x] `_UNSET` has a proper sentinel type (`_UnsetType` in `core/grid.py`)
- [x] YAML values in `load_brand()` are validated before constructing Pydantic models (`base_pptx` type check)
- [x] `slides_factory/exceptions.py` exists with 8 domain exceptions
- [x] Library `ValueError`/`KeyError` calls updated to domain exceptions (`BrandRequiredError`, `GridOverflowError`, `AppNotConfiguredError`)
- [x] CLI commands catch `(SlidesFactoryError, ValueError, KeyError, IndexError, FileNotFoundError)` — not bare `Exception`
- [x] `read_metadata()` emits a `warnings.warn()` on JSON decode failure
- [x] Import-chain smoke test exists in `tests/test_imports.py` (38 modules)
- [x] Test for `ensure_default_theme()` idempotency in `tests/test_default_theme_idempotent.py`
- [x] Test for corrupted metadata decode in `tests/test_default_theme_idempotent.py`
- [x] All tests pass (187/187: 145 original + 42 new)
