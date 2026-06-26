# Skill 01 — Project Setup

## Package Structure

An implementation package follows standard Python packaging conventions.
Here's the recommended layout:

```
my_slides/
├── pyproject.toml
├── my_slides/
│   ├── __init__.py              # SlideFactory instance (auto-discovers subpackages)
│   ├── brand.yaml               # Brand theme (colors, fonts, logos)
│   ├── elements/
│   │   ├── __init__.py
│   │   └── chart.py             # Custom elements (optional)
│   ├── frames/
│   │   ├── __init__.py
│   │   ├── branded.py           # Branded page shells
│   │   └── cover.py
│   └── templates/
│       ├── __init__.py
│       ├── kpi.py               # Grid-based templates
│       ├── agenda.py
│       └── section.py

```

## `pyproject.toml`

```toml
[project]
name = "my-slides"
version = "0.1.0"
description = "My organization's slide factory implementation"
requires-python = ">=3.10"
dependencies = [
    "slides-factory>=0.2.0",
    # plus any additional dependencies:
    # "matplotlib",            # if you render charts 
    # "Pillow",                # if you process raster images
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## The `SlideFactory` Instance

The entry point creates a `SlideFactory`. Templates, frames, and elements
are **auto-discovered** from the caller's package by convention — no explicit
discovery calls needed:

```python
# my_slides/__init__.py
from pathlib import Path
from slides_factory.app import SlideFactory

app = SlideFactory(
    "my_slides",
    help="My organization's deck builder",
    preview_impl_module="my_slides",    # optional: streamlit preview support
    preview_brand=Path(__file__).parent / "brand.yaml",
    preview_page_title="My Slides",
)
```

## What Happens on Import

When Python imports `my_slides`:

1. `SlideFactory("my_slides")` runs, which:
   - Registers built-in elements (`text`, `card`)
   - Stores the caller's package (`my_slides`) for lazy discovery
   - **No global singleton** — the app must be passed explicitly
2. On **first catalog access** (e.g. `list_templates()`, `get_template()`, etc.)
   the framework lazily imports all modules under:
   - `my_slides/templates/` — auto-discovered via `@app.template` decorators
   - `my_slides/frames/` — auto-discovered via `@app.frame` decorators
   - `my_slides/elements/` — auto-discovered via `@app.element` decorators
3. Any implementation package that `import`s `my_slides` can access the app
   via the `app` variable exposed in `my_slides.__init__`.

> **Why lazy discovery?** Submodules (e.g. `my_slides.templates.kpi`) often
> do `from my_slides import app`. Lazy discovery ensures the app is fully
> initialised before submodules are imported, avoiding circular imports.

## Running the CLI

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
my-slides = "my_slides.__main__:main"
```

Where `main()` calls `app.run()`. The `slides-factory` package itself provides
**no** CLI entry point — the CLI belongs entirely to your implementation.

## Testing

In tests, pass the app explicitly — no global state to manage:

```python
from my_slides import app

def test_template(app=app):
    tpl = app.get_template("kpi")
    assert tpl.name == "KPI Dashboard"
```

## Verifying It Works

```python
from my_slides import app

print(app.list_templates())   # => [<SlideTemplate 'kpi'>, ...]
print(app.list_frames())      # => [<FrameTemplate 'branded'>, ...]
print(app.list_elements())    # => [<Element 'text'>, <Element 'card'>, ...]
```

## CLI Entry Point

The CLI is auto-generated from the `SlideFactory` instance. Call `app.run()`
to launch it. Create a `__main__.py`:

```python
# my_slides/__main__.py
from my_slides import app

app.run()
```

Then run:

```console
$ python -m my_slides doc create --help
```

Or register a console script in `pyproject.toml`:

```toml
[project.scripts]
my-slides = "my_slides.__main__:main"
```

Where `main()` calls `app.run()`.

```console
$ my-slides doc create --help
```

> `slides-factory` itself provides **no** CLI entry point. No `__main__.py`,
> no console scripts. The CLI belongs entirely to your implementation.
> Run it via `python -m my_slides ...` or `my-slides ...`.
