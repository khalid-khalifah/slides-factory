# Skill 07 — App Lifecycle

This skill explains how `SlideFactory` works under the hood: the global
singleton, template/frame/element registration, and the discovery mechanism.

## The `_active_app` Singleton

When any `SlideFactory` is created, it sets itself as the module-level global:

```python
# slides_factory/app.py
_active_app: SlideFactory | None = None

class SlideFactory:
    def __init__(self, name, ...):
        global _active_app
        _active_app = self       # ← becomes the "active" app
        self._templates = {}
        self._frames = {}
        self._elements = {}
        self._register_builtins()
        from slides_factory.cli import build_cli
        self.cli = build_cli(self)
```

This enables the module-level helpers (`get_app()`, `list_templates()`,
`get_template()`) to work without explicitly passing an app instance:

```python
from slides_factory.app import get_app

app = get_app()       # returns the most-recently-created SlideFactory
template = app.get_template("kpi")
```

> **Important:** Only one `SlideFactory` should be active at a time.
> Creating a second `SlideFactory` overwrites `_active_app`.

## Registration Flow

### 1. Built-in Elements

Upon construction, `SlideFactory` registers two core elements:

| Kind | Class | Props | Style |
|------|-------|-------|-------|
| `text` | `RegisteredElement` | `TextProps` | `TextStyle` |
| `card` | `RegisteredElement` | `CardProps` | `CardStyle` |

These are always available in every implementation. Custom elements are added
via `@app.element()` or `app._elements["my_kind"] = ...`.

### 2. Templates

Templates register via the `@app.template` decorator, which runs at **import
time**:

```python
# my_slides/templates/kpi.py
from my_slides import app

@app.template("kpi", name="KPI Dashboard", ...)
class Kpi(Template):
    ...
```

When Python imports this module:
1. The `@app.template(...)` decorator factory runs, returning a `decorator` function.
2. The `class Kpi(Template): ...` statement executes, creating the class.
3. The `decorator(Kpi)` call runs, which:
   - Calls `template_from_class(Kpi, app, template_id="kpi", ...)` to build a
     `RegisteredTemplate` wrapper with an auto-generated input model.
   - Stores it in `app._templates["kpi"]`.
   - Stores the source file path in `app._template_sources["kpi"]`.

### 3. Frames

Frames follow the same import-time pattern:

```python
# my_slides/frames/branded.py
from my_slides import app

@app.frame("branded", name="Branded", ...)
def branded(slide, ctx, info): ...
```

When imported, `frame_from_function()` creates a `RegisteredFrame` wrapper
that detects the function's signature arity (how many params it accepts) and
stores it in `app._frames["branded"]`.

### 4. Elements

Elements register similarly:

```python
@app.element("progress_bar", props_model=..., style_model=...)
def render_progress_bar(slide, box, props, style, ctx): ...
```

`element_from_function()` creates a concrete `Element` subclass and stores it
in `app._elements["progress_bar"]`.

## Auto-Discovery

Discovery is **automatic and lazy** — it happens on first catalog access
(e.g. `list_templates()`, `get_template()`, `impl_base_package`), not during
`SlideFactory.__init__()`. This avoids circular imports when submodules do
`from my_pkg import app`.

### How It Works

When `SlideFactory("my_slides")` is created in `my_slides/__init__.py`:

1. `_find_caller_package()` walks the call stack to find the first module
   outside `slides_factory` and extracts its `__package__` (e.g. `my_slides`).
2. The factory stores this as `_caller_package` but **does not import anything yet**.
3. On first catalog access, `_ensure_discovered()` is called, which imports:
   - `my_slides.templates` (every non-`_`-prefixed module)
   - `my_slides.frames`
   - `my_slides.elements`

```python
def _ensure_discovered(self) -> None:
    if self._lazy_discovery_done:
        return
    self._lazy_discovery_done = True
    if self._caller_package is None:
        return
    for subpkg_name in ("templates", "frames", "elements"):
        self._discover_subpackage(f"{self._caller_package}.{subpkg_name}")
```

This means:

- **Any module placed in `templates/`, `frames/`, or `elements/` gets auto-imported.**
- **Decorators fire on import**, populating the app's registries.
- **Subpackages are scanned** (only direct modules, not recursive).
- Empty or missing subpackages are silently skipped.

### Excluding Modules

Files prefixed with `_` are excluded by convention:

```python
# my_slides/templates/_ignored.py — not discovered
```

## Resolution Order

### Frame Resolution

When a slide is created without an explicit frame, `resolve_frame_id()`
applies this precedence:

1. CLI `--frame` argument
2. Stored frame (from existing slide metadata)
3. Template's `default_frame` class attribute
4. Brand's `default_frame` YAML field
5. Hard-coded fallback: `"basic"`

### Template Lookup

`get_template(template_id)` raises `KeyError` with a helpful message listing
all available IDs:

```python
>>> app.get_template("missing")
KeyError: "Unknown template 'missing'. Available: cover, kpi, agenda, section"
```

## Lifecycle Diagram

```
Import an implementation package
        │
        ▼
SlideFactory(name) created
        │
        ├── _active_app = self
        ├── _register_builtins()       # text, card elements
        ├── _caller_package = "my_pkg" # from call-stack inspection
        └── build_cli(self)            # Typer CLI app
        │
        ▼ (no explicit discovery calls — lazy on first catalog access)
        │
First catalog access (list_templates / get_template / impl_base_package ...)
        │
        ▼
_ensure_discovered()
        │
        ├── import my_pkg.templates     # → walks modules, fires @app.template
        ├── import my_pkg.frames        # → walks modules, fires @app.frame
        └── import my_pkg.elements      # → walks modules, fires @app.element
        │
        ▼
Each imported module fires decorators:
        │
        ├── @app.template("kpi", ...) → app._templates["kpi"] = ...
        ├── @app.frame("branded", ...) → app._frames["branded"] = ...
        └── @app.element("chart", ...) → app._elements["chart"] = ...
        │
        ▼
App is ready. CLI commands, preview, and document API
all use get_app() → the active SlideFactory.
```

## Concurrent Apps

In test environments, you may need to swap `_active_app` temporarily:

```python
import slides_factory.app as app_module

original = app_module._active_app
try:
    app_module._active_app = my_test_app
    # ... test code that calls get_app() ...
finally:
    app_module._active_app = original
```

The test `conftest.py` fixture pattern does this automatically:

```python
@pytest.fixture(autouse=True)
def _activate_test_app():
    app_module._active_app = test_app
    yield
    # teardown — ideally restore original, but in practice tests
    # tear down and the next test fixture overwrites it again
```
