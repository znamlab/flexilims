# Agent Guidelines

## Changelog
- Update `CHANGELOG.md` under `# Unreleased` whenever making changes that are important enough to mention to users or maintainers (bugfixes, new features, API or behavior changes, deprecations, significant performance/CI/test changes).
- Skip changelog entries for trivial internal refactors, typo-only edits, or temporary WIP changes.

## Git
- Never run `git commit` autonomously. Always present the changes (or stage them if requested) and wait for explicit human confirmation before committing.

## Development Checks
- Run `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`, and `uv run pytest tests/test_offline.py tests/test_unit.py` (with `-k "not test_download_database or test_download_database_pagination or test_download_database_offset_pagination_and_orphans"` when offline/without `flexiznam` credentials) before committing.
- Note that `pyproject.toml` sets `filterwarnings = ["error"]`, so unexpected warnings will fail tests.
