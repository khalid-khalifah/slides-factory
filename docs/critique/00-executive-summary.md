# Architectural Critique — Executive Summary

**Project:** slides-factory v0.2.0  
**Date:** 2026-06-21  
**Scope:** Full library — 7,110 lines across 55+ Python modules

---

## Blunt Assessment

slides-factory is an ambitious, architecturally interesting project with a clear
separation-of-concerns vision — FastAPI-style decorator registration, a
grid+element render pipeline, and brand-agnostic frame system. However, it
suffers from **severe over-engineering**: a simple slide-generation library has
ballooned into a framework with its own DI container, a CLI builder DSL,
class-based template metaprogramming, and a token-resolution engine that shadows
a YAML-based brand theme system that already does color resolution.

There are **two independent color-resolution systems** in the codebase, one of
which (`core/resolver.py` + `core/tokens.py`) is completely orphaned — no
production code calls it, yet it has its own test file. The global `_active_app`
singleton, coupled with module-level `get_app()` calls throughout the document
facade, creates a fragile import-time dependency graph. State is spread across
three inconsistent persistence mechanisms (speaker notes, core property
keywords, runtime objects).

The codebase has clearly evolved through iteration without periodic pruning.
**~40-50% of the complexity is unnecessary.** It is not production-ready without
a deliberate round of ruthless simplification.

## Scorecard

| Category | Score | Rationale |
|---|---|---|
| **Maintainability** | **4/10** | Dead code, global singleton antipattern, tangled import chains, and ~7,100 lines for what is fundamentally a ~2,000–3,000-line library. Onboarding a new developer takes days. |
| **Pythonic Idiom** | **6/10** | Good Pydantic/dataclass/ABC usage. But `if False:` typing guard, barrel re-exports, manual function-arity introspection, and dead OOP-style resolver are not Pythonic. |
| **Architecture & Modularity** | **5/10** | Clean conceptual layering (engine → grid → layout → elements), but the implementation leaks abstractions. Two parallel color systems, a God-module `document.py`, and a `SlideFactory` that is simultaneously a DI container, CLI builder, and global singleton. |
| **Robustness (Error Handling/Testing)** | **5/10** | 30+ test files is commendable, but tests cover dead code. The CLI swallows exceptions with blanket `except Exception:`. No logging infrastructure. Error types are generic `ValueError` instead of domain-specific exceptions. |

## Key Metrics

| Metric | Value |
|---|---|
| Total Python files (library) | 55 |
| Total lines of Python | ~7,110 |
| Test files | 30 |
| Dead modules | 2 (`core/resolver.py`, `core/tokens.py`) |
| Dead test files | 1 (`test_theme_resolver.py`) |
| Largest file | `cli.py` (~600 lines) |
| Python minimum version | 3.13 (unnecessarily aggressive) |
| Global singletons | 1 (`_active_app`) |
| Parallel color-resolution systems | 2 (one dead) — Run 4 consolidated the remaining system |
| State persistence mechanisms | 3 (speaker notes, core properties, runtime) |

## Fixing Plan Overview

The fixes are split into **six independent runs**, each self-contained and
mergeable independently. Each run targets a specific category of issues, from
quick wins (dead code removal) to structural refactors (global singleton,
packaging).

| Run | Document | Effort | Risk | Impact | Status |
|-----|----------|--------|------|--------|--------|
| 1 | [01-dead-code-removal.md](01-dead-code-removal.md) | 30 min | Low | High | ✅ Done (PR #1 merged) |
| 2 | [02-global-singleton-refactor.md](02-global-singleton-refactor.md) | 2–3 hours | Medium | Critical | ✅ Done (PR #2 merged) |
| 3 | [03-import-architecture.md](03-import-architecture.md) | 1–2 hours | Medium | High | ✅ Done (pushed to main) |
| 4 | [04-color-system-consolidation.md](04-color-system-consolidation.md) | 1 hour | Low | Medium | ✅ Done (pushed to main) |
| 5 | [05-code-quality-and-testing.md](05-code-quality-and-testing.md) | 2–3 hours | Low | High | ⏳ Pending |
| 6 | [06-packaging-and-tooling.md](06-packaging-and-tooling.md) | 1 hour | Low | Medium | ⏳ Pending |

**Recommended order:** Run 1 → Run 2 → Run 3 → Run 4 → Run 5 → Run 6.  
Runs 4 and 5 can be parallelized after Run 3. Run 6 is safe to do at any time.
