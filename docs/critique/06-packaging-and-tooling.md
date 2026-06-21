# Run 6 — Packaging, Tooling & Project Hygiene

**Effort:** ~1 hour  
**Risk:** Low (additive changes, no logic changed)  
**Impact:** Medium (improves developer experience, distribution, and CI)
**Status:** ✅ **DONE** — committed `80d87f6`, pushed to `main`

---

## Goal

Bring the project's packaging, tooling, and repository hygiene up to modern
Python standards. This includes migration to `src/` layout, adding linting
configuration, loosening the Python version constraint to be practical, and
adding missing `pyproject.toml` metadata.

---

## Step 1: Loosen `requires-python` from `>=3.13` to `>=3.10`

**Current:** `pyproject.toml` line 5:
```toml
requires-python = ">=3.13"
```

**Why this is too aggressive:**
- Python 3.13 was released October 2024; most corporate environments are still on 3.10–3.12
- The code uses no 3.13-specific features: no free-threading, no JIT, no new syntax
- The only feature that might require 3.12+ is `inspect.getfile()` behavior — which is identical in 3.10+
- All dependencies (`pydantic`, `python-pptx`, `typer`, `pyyaml`, `fonttools`, `lxml`, `pillow`) support Python 3.10+

**Action:** Change to:
```toml
requires-python = ">=3.10"
```

**Verification:** Run tests on Python 3.10 (or use `uv venv --python 3.10`):
```bash
uv run pytest tests/
```

If tests pass on 3.10, the version constraint was unnecessarily strict.

---

## Step 2: Add missing `pyproject.toml` metadata

**Current:** `pyproject.toml` is missing `[project.urls]` and classifiers.

**Action:** Add:
```toml
[project.urls]
Homepage = "https://github.com/user/slides-factory"
Source = "https://github.com/user/slides-factory"
Issues = "https://github.com/user/slides-factory/issues"

[project.classifiers]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Multimedia :: Graphics :: Presentation",
]
```

---

## Step 3: Add linting and formatting configuration

### 3a: Add `[tool.ruff]` to `pyproject.toml`

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort (import ordering)
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
    "W",   # pycodestyle warnings
]
ignore = [
    "E501", # line too long (handled by formatter)
    "B008", # do not perform function calls in argument defaults
]

[tool.ruff.lint.isort]
known-first-party = ["slides_factory"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

### 3b: Add ruff to dev dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.8",
]
```

### 3c: Run ruff and fix issues

```bash
uv sync --group dev
uv run ruff check slides_factory/ tests/ --fix
uv run ruff format slides_factory/ tests/
```

### 3d: Add pre-commit config (optional but recommended)

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Step 4: Consider `src/` layout migration

**Current:** Flat layout — `slides_factory/` at repo root.

**Pros of staying flat:**
- Simpler import during development (`uv run python -c "import slides_factory"`)
- No need to update CI

**Cons of flat layout:**
- `slides_factory/` on PYTHONPATH can shadow the installed version
- Cannot easily ship multiple packages from the same repo

**Recommendation for v0.2.x:** Stay flat for now. If the project is split into
`slides-factory-core` and `mim-slides` as separate packages in a monorepo,
migrate to `src/` then.

**If you decide to migrate now:**

1. Create `src/slides_factory/` and move all files
2. Update `pyproject.toml`:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src/slides_factory"]
   ```
3. Update test imports — pytest needs `src/` on `PYTHONPATH`:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   pythonpath = ["src"]
   ```
4. Update all internal absolute imports (they should already be `slides_factory.*` — verify)

**Decision:** Mark this as "for future consideration" and skip for this run.
Focus on the low-risk changes in Steps 1–3.

---

## Step 5: Add `.gitignore` entries for generated files

**Current:** No `.gitignore` entries for `.pptx` output, coverage files, or
editor config files.

**Action:** Add to `.gitignore`:
```gitignore
# Slide output files
*.pptx

# Coverage
.coverage
htmlcov/
.coverage.*

# Editor
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.egg-info/
dist/
build/
```

**Note:** `themes/default.pptx` is committed intentionally (it's a base theme
asset, not generated output). If using `*.pptx` in `.gitignore`, add an
exception:
```gitignore
!themes/default.pptx
```

---

## Step 6: Verify `themes/default.pptx` is included in the wheel

**Current:** `[tool.hatch.build.targets.wheel]` only lists `packages =
["slides_factory"]`, which excludes `themes/`.

**Verification:**
```bash
uv build
python -c "import zipfile; z = zipfile.ZipFile('dist/*.whl'); print([n for n in z.namelist() if 'themes' in n])"
```

If `themes/default.pptx` is not in the wheel, add it to `[tool.hatch.build.targets.wheel]`:
```toml
[tool.hatch.build.targets.wheel]
packages = ["slides_factory"]
artifacts = ["themes/default.pptx"]
```

Or better: configure hatch to include the themes directory:
```toml
[tool.hatch.build.targets.wheel]
packages = ["slides_factory"]
include = ["themes/"]
```

---

## Step 7: Add CI configuration improvements

**Current:** `.github/workflows/ci.yml` exists (verify it covers multiple Python
versions).

**Action:** After loosening `requires-python` to `>=3.10`, add a matrix build:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]

steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
  - run: pip install uv
  - run: uv sync --group dev
  - run: uv run pytest
  - run: uv run ruff check slides_factory/ tests/
```

---

## Acceptance Criteria

- [x] `requires-python` changed to `>=3.10` (all 187 tests pass)
- [x] `[project.urls]` added (Homepage, Source, Issues)
- [x] `[project.classifiers]` added (7 classifiers)
- [x] `[tool.ruff]` configuration added (E, F, I, B, C4, SIM, W selectors)
- [x] `ruff` added to `dev` dependencies
- [x] `ruff check` and `ruff format` pass with zero errors (58 auto-fixed + 9 manual fixes)
- [x] `.gitignore` includes `*.pptx` with `!themes/default.pptx` exception
- [x] `themes/default.pptx` verified in built wheel via `force-include` in hatch config
- [x] CI runs on Python 3.10, 3.11, 3.12, 3.13 (matrix strategy)
- [x] Pre-commit config added (`.pre-commit-config.yaml` with ruff + ruff-format hooks)

---

## Future Considerations (Not This Run)

- **`src/` layout migration** — Only when splitting into monorepo packages
- **`themes/default.pptx` generation** — Generate from code instead of
  committing a binary. Use `python-pptx` to create a blank template.
- **`uv.lock` comment** — Add a comment in `pyproject.toml` indicating the
  lockfile is for development only (packages should not have lockfiles in
  distributed wheels).
