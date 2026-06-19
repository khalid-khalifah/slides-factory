# 02: Dynamic Model Magic

## The Issue
In `registration.py`, the project uses Pydantic's `create_model` to dynamically generate input models at runtime based on a template class's methods and their associated element kinds.

## Why it Matters
This creates a "blind spot" for every tool in the modern Python ecosystem:
- **No Autocomplete**: IDEs cannot know what fields exist on a dynamic model, so developers get no hints when writing data for templates.
- **Static Analysis Failure**: Tools like `mypy` or `pyright` cannot validate that the data being passed to a template matches its required schema.
- **Runtime Fragility**: Errors are only caught at runtime during validation, rather than during development.

## Proposed Solutions

### Option A: Explicit Input Models (Recommended)
Require every `Template` subclass to define an explicit Pydantic model for its input. Use Generics to ensure type safety throughout the render pipeline.

**Example:**
```python
class KpiInput(BaseModel):
    title: str
    revenue: RevenueElementProps

class KpiTemplate(Template[KpiInput]):
    input_model = KpiInput
```

### Option B: Type-Hinted Method Return Types
Instead of dynamic model generation, use the type hints of the `@at` methods to build a registry of required types. While still dynamic, it allows for better introspection and potential plugin support for IDEs via custom LSP extensions (though this is significantly higher effort).
