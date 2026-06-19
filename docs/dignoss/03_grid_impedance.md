# 03: The CSS Grid Impedance Mismatch

## The Issue
The project uses CSS-like strings (e.g., `"grid-cols-1 grid-rows-[1_2] gap-4"`) to define layouts in a coordinate-based environment (PowerPoint). This essentially implements a custom layout engine that translates "web-style" flow into absolute EMU coordinates.

## Why it Matters
PowerPoint is not HTML. Trying to force a flow-based mental model onto it creates several risks:
- **Boundary Issues**: Text overflow or varying content lengths can easily break the calculated grid, leading to overlapping elements.
- **Validation Gap**: Because layout logic is hidden in strings, errors (like conflicting column spans) are only discovered during the actual rendering process.
- **Complexity Leak**: The `render_layout` function must become increasingly complex to handle "edge cases" that wouldn't exist if using a coordinate or percentage-based system.

## Proposed Solutions

### Option A: Structured Layout Objects (Surgical)
Replace raw strings with structured Pydantic objects (`GridSpec`). This moves validation from "render-time" to "definition-time."

**Example:**
```python
grid = GridSpec(cols=1, rows=[1, 2], gap=4)
```

### Option B: Percentage/Anchor System (Strategic)
Shift from a "Grid" metaphor to an "Anchor and Offset" metaphor. Define elements by their relative position (e.g., `top=10%, left=5%, width=20%`). This is more native to how slide software works and avoids the need for a complex grid-calculation engine.
