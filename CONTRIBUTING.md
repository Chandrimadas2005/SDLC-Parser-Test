# Contributing

## Code rules and how they are enforced

| Rule | Limit | Enforced by |
|---|---|---|
| Method length | 18 lines or fewer (docstring, blank and comment lines not counted) | `tools.CodeRules` (CR001) |
| Parameters | 3 or fewer, `self` excluded; use a frozen dataclass for more | ruff `PLR0913`, `PLR0917` |
| Complexity | 4 or less; use guard clauses and early returns | ruff `C901` |
| try/except | One per method; never catch `Exception` | `tools.CodeRules` (CR002), ruff `BLE001` |
| Types | Hints everywhere, `mypy --strict`, no `Any` | mypy (`disallow_any_explicit`), ruff `ANN` |
| Keys and names | From `StrEnum`; no literal string keys | review |
| Domain values | Value objects (frozen dataclasses), not bare `str` or `int` | review |
| Defaults | `None`, except in `__init__` or class constants; never mutable | ruff `B006`, `B008`, review |
| Docs | Google-style docstring on every public method | ruff `D` (google convention) |
| Logging | `structlog`; never `print()`; no document content in logs | ruff `T20`, review |
| Dependencies | Constructor injection only; ports are `typing.Protocol` | review |
| Layers | `Infrastructure -> Application -> Domain`; Domain has no outside imports | import-linter |
| Files | One public class per file, file name equals class name, no top-level functions | `tools.CodeRules` (CR003-CR005) |
| Packages | PascalCase, `__init__.py` with `__all__`, no `utils` or `common` | `tools.CodeRules` (CR006-CR008) |
| Licences | MIT, BSD, Apache-2.0, ISC or PSF for everything that ships | CI `pip-licenses` |

## Git

- Never commit to the default branch. One branch per piece of work, named
  `<type>/<scope>-<topic>`, e.g. `feature/parser-xlsx-extractor`.
  Types: `feature`, `fix`, `chore`, `docs`, `test`, `ci`.
- Micro commits (about 150 changed lines or fewer, lockfiles excluded) in Conventional
  Commits format: `type(scope): imperative summary`, 72 characters or fewer.
- Tests go in the same commit as the code. Every commit passes lint and tests.
- No force push, no `--no-verify`, no secrets or real data. Only `.env.example` with
  synthetic values is committed.
- Changes to the shared Domain contracts go through a small dedicated branch reviewed by
  both track owners before the lead review.

## Self-check before opening a pull request

```bash
uv run pre-commit run --all-files
```

This runs the same checks as CI: ruff, mypy, import-linter, code rules and pytest.

## Review before merge

1. Finish the branch; every commit leaves lint, types and tests passing.
2. Open a pull request using the template (branch, what and why, commits, testing,
   results, open points).
3. The other track owner reviews first, then the lead.
4. Fix comments with new commits on the same branch. Do not rewrite shared history.
5. Only the lead merges.
