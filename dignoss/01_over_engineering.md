# 01: The Framework Trap (Over-Engineering)

## The Issue
The project has implemented a heavy Domain Specific Language (DSL) using `@at` decorators and class-based template definitions to describe PowerPoint slides. While elegant, it forces every slide creation through a specific object-oriented pipeline.

## Why it Matters
When you build a "Framework" instead of a "Library," you introduce **cognitive load** and **rigidity**. 
- **Rigidity**: If a user needs a layout that doesn't fit the "Grid + Element" mental model, they are blocked by the framework's constraints.
- **Complexity**: New contributors must learn the specific meaning of `@at` and the internal registration lifecycle before they can add a simple slide.
- **Overhead**: The amount of code required to support the DSL (registration, introspection, wrapper classes) outweighs the actual logic of drawing shapes on a slide.

## Proposed Solutions

### Option A: Functional First (Surgical)
Introduce a purely functional API that does not require classes or decorators. The class-based system becomes "syntactic sugar" on top of this functional core.

**Example:**
Instead of requiring `class Kpi(Template)`, allow:
```python
render_template(slide, layout=KPI_LAYOUT_SPEC, data=kpi_data, ctx=ctx)
```

### Option B: Configuration over Code (Strategic)
Move template definitions out of Python classes and into JSON/YAML files. 
- Define the grid and elements in a config file.
- Use Python only for the "Render Functions" that handle specific element kinds.
- This separates the *structure* of the slide from the *logic* of the rendering.
