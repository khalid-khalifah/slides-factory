# Refactor Plan: Explicit App Everywhere

## Current State

There are 27 call sites that depend on `_active_app` / `get_app()` across 8 files:

| File | Dependency | Usage |
|------|-----------|-------|
| `app.py` | `_active_app`, `get_app()`, `AppNotConfiguredError` | Singleton + 1 function |
| `template.py` | `get_app()` | 4 function pairs with fallback |
| `frame.py` | `get_app()` | 2 function pairs with fallback |
| `document.py` | `get_app()` | 5 functions with lazy import fallback |
| `layout/render.py` | `get_app()` | Default arg fallback in `render_layout()` |
| `core/grid.py` | `get_app()` | 2 lazy imports in `GridSlideService` |
| `cli.py` | (indirect — uses `factory` param) | Already explicit via `build_cli(factory)` |
| `preview/launcher.py` | `get_app()` | Module-level call |

---

## Goal

- `_active_app` / `get_app()` removed
- `app.run()` is the CLI
- Every function that needs an `app` receives it explicitly as a parameter
- No fallback to a global — if you don't have an app, you can't call it

---

## Phase 1 — Core: `app.py`

### 1a. Remove `_active_app` and `get_app()`

```diff
- _active_app: SlideFactory | None = None
- 
- def get_app() -> SlideFactory:
-     if _active_app is None:
-         raise AppNotConfiguredError(
-             "No slide factory app configured. Import an implementation package "
-             "(e.g. mim_slides) before using the catalog or CLI."
-         )
-     return _active_app
```

### 1b. Remove `_active_app = self` from `__init__()`, remove `build_cli(self)` call

```diff
  def __init__(self, name, ...):
-     global _active_app
-     _active_app = self
      ...
-     from slides_factory.cli import build_cli
-     self.cli = build_cli(self)
```

### 1c. Add `app.run()` method

```python
class SlideFactory:
    def run(self, args: list[str] | None = None) -> None:
        """Run the CLI for this factory."""
        from slides_factory.cli import build_cli
        build_cli(self)(args)
```

### 1d. Add `app.preview()` method

```python
class SlideFactory:
    def preview(
        self,
        brand_path: Path | None = None,
        page_title: str | None = None,
        extra_args: list[str] | None = None,
    ) -> int:
        """Launch the Streamlit preview for this factory."""
        from slides_factory.preview.run import run_preview
        return run_preview(
            impl_module=self.preview_impl_module,
            brand_path=brand_path or self.preview_brand,
            page_title=page_title or self.preview_page_title,
            extra_args=extra_args,
        )
```

### 1e. Remove `AppNotConfiguredError` from `exceptions.py` (optional, keep if used elsewhere)

---

## Phase 2 — No Entry Points for `slides_factory`

`slides_factory` is a **library**, not a CLI tool. It does **not** provide:
- `__main__.py`
- Console scripts (`[project.scripts]`)
- Any `$ python -m slides_factory ...` interface

The CLI is an affordance of the **implementation package**, which calls
`app.run()` from its own entry point.

### How implementation packages expose the CLI

The implementation package owns the entry point:

```python
# my_slides/__main__.py
from my_slides import app

app.run()
```

```console
$ python -m my_slides doc create --help
```

Or via a console script in the implementation's `pyproject.toml`:

```toml
[project.scripts]
my-slides = "my_slides.__main__:entry_point"
```

Where the implementation provides a thin shim that calls `app.run()`.
`slides_factory` does not install any global `sf` or `slides-factory` binary.

### 2c. Update `preview/launcher.py`

Remove the `get_app()` call at module level. The launcher is spawned by `app.preview()` which passes the env vars. The launcher either:
- Imports the impl module and accesses `impl.app` (same convention)
- Or is refactored to be a method on `SlideFactory` entirely

```python
"""Now imports the impl module and accesses its app attribute."""
impl_module = os.environ.get("SLIDES_FACTORY_IMPL")
if not impl_module:
    raise RuntimeError("SLIDES_FACTORY_IMPL not set")
impl = importlib.import_module(impl_module)
app = impl.app

run_preview_app(
    app,
    brand_path=Path(os.environ["SLIDES_FACTORY_PREVIEW_BRAND"]) if os.environ.get("SLIDES_FACTORY_PREVIEW_BRAND") else None,
    page_title=os.environ.get("SLIDES_FACTORY_PREVIEW_TITLE"),
)
```

---

## Phase 3 — Module-Level Helpers

### 3a. `template.py` — make `app` required, remove fallback

```diff
- def list_templates(*, tag: str | None = None, app: object | None = None) -> list[Any]:
-     if app is not None:
-         if hasattr(app, "list_templates"):
-             return app.list_templates(tag=tag)
-         from slides_factory.app import get_app
-         return get_app().list_templates(tag=tag)
-     from slides_factory.app import get_app
-     return get_app().list_templates(tag=tag)

+ def list_templates(app: SlideFactory, *, tag: str | None = None) -> list[Any]:
+     return app.list_templates(tag=tag)
```

Same treatment for `get_template()`, `list_tags()`, `search_templates()`.

### 3b. `frame.py` — make `app` required, remove fallback

```diff
- def list_frames(*, app: object | None = None) -> list[FrameTemplate]:
-     if app is not None:
-         if hasattr(app, "list_frames"):
-             return app.list_frames()
-         ...
-     return get_app().list_frames()

+ def list_frames(app: SlideFactory) -> list[FrameTemplate]:
+     return app.list_frames()
```

Same for `get_frame()`.

### 3c. `document.py` — make `app` required, remove fallback

Every function that currently has `app=None` with a lazy `get_app()` fallback gets `app` as a required parameter:

- `add_slide(prs, template_id, data, *, ..., app)` — `app` already exists but optional
- `add_frame_slide(prs, frame, data, *, ..., app)` — same
- `edit_slide(prs, index, ..., app)` — same
- `add_element_slide(prs, ...)` — check if it uses get_app
- `list_slides_info()` — check

These become:
```python
def add_slide(prs, template_id, data, *, ..., app: SlideFactory) -> dict:
    ...
```

**Impact on callers:** The CLI (`cli.py`) and tests pass `app` explicitly — they already have access to the factory instance.

### 3d. `layout/render.py` — make `app` required

```diff
- def render_layout(slide, layout, ctx, *, app=None):
-     app = app if app is not None else get_app()
+ def render_layout(slide, layout, ctx, *, app: SlideFactory):
```

**Callers of `render_layout()`:**
- `Templating.py:Template.render()` — called via `render_layout(slide, self.build(data), ctx)`. The `Template` class needs access to the app. Currently it doesn't have it — it uses the module-level function which falls back to `get_app()`. 
  
  This is a key design question: how does `Template.render()` get the app? Options:
  1. Store `app` on the `Template` instance (passed during registration)
  2. Store `app` on the registered wrapper (currently `template_from_class` builds the wrapper)
  3. Pass `app` to `Template.render()` explicitly

  Looking at how `template_from_class` works in `registration.py`, the wrapper stores the app:
  ```python
  # registration.py creates a RegisteredTemplate that wraps the class
  registered.app = app  # stored on the wrapper
  ```
  
  So the wrapper already has access to the app. We need to thread it through to `render_layout()`.

### 3e. `core/grid.py` — accept existing `app`, remove fallback

```diff
- class GridSlideService:
-     def __init__(self, prs, *, app=None):
-         ...
-         if app is None:
-             from slides_factory.app import get_app
-             app = get_app()
-         self.app = app
+ class GridSlideService:
+     def __init__(self, prs, *, app: SlideFactory):
+         self.app = app
```

**Callers of `GridSlideService()`:**
- `core/engine.py:LayoutEngine.__init__()` — already has `app` parameter
- Tests — need to pass `app=` explicitly

Same for `RAW_LAYOUT_ID` service in `core/grid.py`.

---

## Phase 4 — Update all Callers

### 4a. `cli.py`

Already passes `factory` explicitly via `build_cli(factory)`. No change to the function body — just update the entry point.

### 4b. `core/engine.py`

`LayoutEngine.__init__(self, prs, *, app=None)` → make `app` required.

**Callers of `LayoutEngine()`:**
- `document.py:add_slide()`, `edit_slide()`, etc. — already have `app` after Phase 3c

### 4c. Tests

**Remove the conftest fixture that sets `_active_app`:**

```diff
  # tests/conftest.py
- @pytest.fixture(autouse=True)
- def _activate_core_app():
-     core_app_module = importlib.import_module("tests.fixtures.app")
-     app_module._active_app = core_app_module.app
-     yield
```

**Update all callers of module-level helpers to pass `app=`:**

| Old | New |
|-----|-----|
| `list_templates()` | `list_templates(app)` |
| `get_template("kpi")` | `get_template(app, "kpi")` |
| `list_frames()` | `list_frames(app)` |
| `get_frame("branded")` | `get_frame(app, "branded")` |
| `document.add_slide(prs, "kpi", data, frame="x")` | `document.add_slide(prs, "kpi", data, frame="x", app=app)` |

**Tests that already have access to `app`:**
- `test_app.py` — uses `get_app()` which will be removed. Replace with `test_fixtures.app.app` or the `app` fixture
- `test_cli_builder.py` — passes `cli_runner.invoke(factory.cli, ...)`. Will need to change to `factory.run(["doc", ...])` or build CLI inline
- `test_document.py` — uses `app` fixture from conftest
- `test_registration.py` — creates its own `SlideFactory`, passes explicit
- `test_templating.py` — creates its own `SlideFactory`
- `test_preview_reload.py` — already passes `factory` explicitly

---

## Phase 5 — `Preview` Module

### 5a. `preview/launcher.py`

Change from `get_app()` to `impl.app`:

```python
impl = importlib.import_module(impl_module)
app = impl.app   # Convention: impl module exposes an `app` attribute
run_preview_app(app, ...)
```

### 5b. `preview/run.py`

No change — already takes explicit params.

### 5c. `preview/reload.py`

No change — already takes explicit `factory`.

### 5d. `preview/app.py`

No change — already takes explicit `app` parameter in function signatures.

---

## Phase 6 — Cleanup

### 6a. Remove unused imports

- `template.py`: remove `from slides_factory.app import get_app`  
- `frame.py`: remove `from slides_factory.app import get_app`  
- `document.py`: remove `from slides_factory.app import get_app`  
- `layout/render.py`: remove `from slides_factory.app import get_app`  
- `core/grid.py`: remove `from slides_factory.app import get_app`  
- `preview/launcher.py`: remove `from slides_factory.app import get_app`  
- `app.py`: remove `from slides_factory.exceptions import AppNotConfiguredError`

### 6b. Remove `AppNotConfiguredError` from `exceptions.py`

If it's no longer used anywhere. Check with `grep -rn "AppNotConfiguredError"`.

---

## Migration Guide

### Before (current)

```python
# my_slides/__init__.py
from slides_factory.app import SlideFactory

app = SlideFactory("my_slides")          # sets _active_app globally

# CLI invocation — implementation package owns the entry point
$ python -m my_slides doc create ...     # calls app.cli() internally
```

### After

```python
# my_slides/__init__.py
from slides_factory.app import SlideFactory

app = SlideFactory("my_slides")          # no global side effects

# CLI invocation — same, but app.run() replaces app.cli
# my_slides/__main__.py:
#   from my_slides import app
#   app.run()
$
$ python -m my_slides doc create ...

# Or via console_scripts in my_slides' pyproject.toml:
# [project.scripts]
# my-slides = "my_slides.__main__:entry_point"
$ my-slides doc create ...
```

## Breaking Changes Summary

| API | Change |
|-----|--------|
| `slides_factory.app.get_app()` | **Removed** |
| `slides_factory.app._active_app` | **Removed** |
| `slides_factory.exceptions.AppNotConfiguredError` | **Removed** (no longer needed) |
| `SlideFactory.cli` | **Removed** from `__init__`. Use `app.run()` instead. |
| `template.list_templates(app=None)` | **Required** `app` parameter (positional or keyword) |
| `template.get_template(id, app=None)` | **Required** `app` parameter |
| `template.list_tags(app=None)` | **Required** `app` parameter |
| `template.search_templates(q, app=None)` | **Required** `app` parameter |
| `frame.list_frames(app=None)` | **Required** `app` parameter |
| `frame.get_frame(id, app=None)` | **Required** `app` parameter |
| `document.add_slide(..., app=None)` | **Required** `app` parameter |
| `document.add_frame_slide(..., app=None)` | **Required** `app` parameter |
| `document.edit_slide(..., app=None)` | **Required** `app` parameter |
| `layout.render.render_layout(..., app=None)` | **Required** `app` parameter |
| `core.grid.GridSlideService(prs, *, app=None)` | **Required** `app` parameter |
| `core.engine.LayoutEngine(prs, *, app=None)` | **Required** `app` parameter |
| `cli.py:main()` | Replaced by `__main__.py` entry point |

## Estimated Effort

| Phase | Files | Changes | Risk |
|-------|-------|---------|------|
| 1 — Core app.py | 1 | ~20 lines | Low |
| 2 — Entry points | 3 | ~40 lines | Low |
| 3 — Module helpers | 4 | ~80 lines | Medium (parameter changes ripple) |
| 4 — Callers | ~15 | ~50 lines | Medium (many small changes) |
| 5 — Preview | 1 | ~15 lines | Low |
| 6 — Cleanup | ~8 | ~30 lines | Low |
| **Total** | **~20 files** | **~235 lines** | **Medium** |
