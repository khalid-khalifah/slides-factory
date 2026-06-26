# Skill 07 — App Lifecycle

This skill explains how `SlideFactory` works under the hood: how templates,
frames, and elements register, how the CLI is launched, and the explicit app
pattern.

## No Global Singleton

`SlideFactory` does **not** set any global state. No `_active_app`, no `get_app()`.
Every function that needs the app receives it as an explicit parameter:

```python
app.list_templates()
app.get_template("kpi")
app.get_frame("branded")
app.run()                         # launches the CLI
```

Module-level helpers (`get_template()`, `get_frame()`, etc.) also require an
explicit `app` parameter:

```python
from slides_factory.frame import get_frame
frame = get_frame(app, "branded")
```

This means:
- **No global state** — each `SlideFactory` is self-contained
- **Testable** — no need to swap singletons in conftest
- **Multiple apps** — you could (in theory) create two factories in one process
- **No `AppNotConfiguredError`** — if you don't have an app, you can't call it

## Registration Flow

### 1. Built-in Elements

Upon construction, `SlideFactory` registers two core elements:

| Kind | Props | Style |
|------|-------|-------|
| `text` | `TextProps` | `TextStyle` |
| `card` | `CardProps` | `CardStyle` |

These are always available. Custom elements are added via `@app.element()`.

### 2. Templates

Templates register via the `@app.template` decorator at **import time**:

```python
# my_slides/templates/kpi.py
from my_slides import app

@app.template("kpi", name="KPI Dashboard", ...)
class Kpi(Template):
    ...
```

When imported:
1. The `@app.template(...)` decorator factory runs, returning a `decorator` function.
2. The `class Kpi(Template): ...` statement executes, creating the class.
3. The `decorator(Kpi)` call:
   - Calls `template_from_class(Kpi, app, ...)` to build a registered wrapper
   - Stores `app` on the class as `Kpi._app` (used later by `Template.render()`)
   - Stores it in `app._templates["kpi"]`
   - Stores the source file path in `app._template_sources["kpi"]`

### 3. Frames

Same import-time pattern:

```python
# my_slides/frames/branded.py
from my_slides import app

@app.frame("branded", name="Branded", ...)
def branded(slide, ctx, info): ...
```

`frame_from_function()` detects the function's signature arity and stores
the frame in `app._frames["branded"]`.

### 4. Elements

```python
@app.element("progress_bar", props_model=..., style_model=...)
def render_progress_bar(slide, box, props, style, ctx): ...
```

`element_from_function()` creates a concrete `Element` subclass and stores
it in `app._elements["progress_bar"]`.

## Auto-Discovery

Discovery is **automatic and lazy** — it happens on first catalog access
(e.g. `list_templates()`, `get_template()`, `impl_base_package`), not during
`SlideFactory.__init__()`. This avoids circular imports when submodules do
`from my_slides import app`.

### How It Works

When `SlideFactory("my_slides")` is created in `my_slides/__init__.py`:

1. `_find_caller_package()` walks the call stack to find the first module
   outside `slides_factory` and extracts its `__package__` (e.g. `my_slides`).
2. The factory stores this as `_caller_package` but **does not import anything yet**.
3. On first catalog access, `_ensure_discovered()` imports:
   - `my_slides.templates` (every non-`_`-prefixed module)
   - `my_slides.frames`
   - `my_slides.elements`

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

`app.get_template(template_id)` raises `KeyError` with a helpful message:

```python
>>> app.get_template("missing")
KeyError: "Unknown template 'missing'. Available: cover, kpi, agenda, section"
```

## CLI Lifecycle

The CLI is **not** built during `__init__()`. The Typer app is created on
demand when `app.run()` or `app.cli` is accessed:

```python
# app.run() builds the CLI and executes it
def run(self, args=None):
    self.cli(args)       # self.cli builds and returns the Typer App

@property
def cli(self):
    from slides_factory.cli import build_cli
    return build_cli(self)   # fresh Typer App each time
```

The implementation package owns the entry point:

```python
# my_slides/__main__.py
from my_slides import app
app.run()
```

`slides-factory` provides **no** `__main__.py` or console scripts — the CLI
belongs entirely to your implementation.

## Lifecycle Diagram

```
Import an implementation package
        │
        ▼
SlideFactory(name) created
        │
        ├── _register_builtins()       # text, card elements
        ├── _caller_package = "my_pkg" # from call-stack inspection
        └── no CLI built yet
        │
        ▼ (lazy discovery on first catalog access)
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
app.run() → build_cli(self) → Typer CLI ready
```

## Testing

Since there's no global singleton, testing is straightforward — just pass the
app explicitly:

```python
# tests/conftest.py
from tests.fixtures.app import app

# No _activate_core_app fixture needed
```

```python
# tests/test_kpi.py
from tests.fixtures.app import app

def test_kpi_builds_layout():
    template = app.get_template("kpi")
    data = template.validate_data({...})
    layout = template.build(data)
    assert len(layout.cells) == 2
```

No `get_app()`, no `_active_app` swapping, no global state to manage.
