# Unreleased

CI:
- Replace the `neuroinformatics-unit/actions` workflows with the reusable
`znamlab/python-uv-ci` workflow (uv-based lint, `ty` type check and tests).
- Run the test suite in CI for the first time: remove the `raise IOError` that
`tests/test_flexilims.py` triggered under GitHub Actions. Crick-network tests stay
skipped there.
- Move the `dev` dependencies from an extra to a PEP 735 dependency group so `uv sync`
installs them, and add the previously undeclared `numpy` plus `ty`.
- Replace mypy with `ty` in pre-commit so the local hook and CI run the same type
checker.
- Replace the tag release workflow: build with `uv build` and attach the sdist and wheel
to the GitHub Release (the old job pointed at a deleted `release_notes.md`).
- Drop `docs_build_and_deploy.yml`, which built Sphinx docs that do not exist.

Bugfixes:
- `parse_error` returns the raw server message instead of raising `AttributeError` when
the response is not the expected html error page, and parses multiline HTML error pages.
- Remove `OfflineFlexilims._format_dataframe`, dead code calling a method that does not
exist.
- Fix attribute validation in `check_flexilims_validity`: use regex whitespace matching,
return a cleaned deep copy instead of mutating caller dicts in place, replace `NaN`
inside lists in `_cleanlist`, and validate `attributes` in `update_one` and `update_key`
in `update_many`.
- Stop mutating caller dicts in place in `format_results`.
- Add default request timeouts (60s, configurable via `timeout`) to `Flexilims` and
`get_token`, use wall-clock deadlines in `update_token`, fail immediately on HTTP
401/403 credentials errors in `get_token`, and refresh expired tokens on both 401 and
403.
- Return non-200 2xx responses from `safe_execute` as warned, and report the actual
request URL on 404.
- Fix `OfflineFlexilims` data integrity and return types: enforce name uniqueness and
validate `origin_id` in `post`, raise `FlexilimsError` on unknown `id` in `update_one`
and `get_children`, re-key renamed entities safely, forward `allow_nulls`/`allow_strings`
to nested dicts, filter `get()` directly in Python (returning deep-copied `list[dict]`
with `origin_id=None` for root entities), and set `"origin_id": None` on posted roots.
- Deduplicate paginated results in `download_database`, keep root `origin_id` as `None`,
and log a warning when orphaned entities (and their descendants) are omitted.

API / Parity:
- Remove the server-rejected `other_relations` parameter from `post()` (online and
offline) and deprecate the unused `project_id` parameter in `update_one()`.
- Add `limit`, `cross_project_entity`, and multi-attribute `query_key`/`query_value`
support to `OfflineFlexilims.get()`, and pass `strict_validation` via `params` in
`post()` and `update_many()`.

Tests:
- Add network-free unit tests in `tests/test_unit.py` and offline regression tests in
`tests/test_offline.py`.

# v1.3

Performance:
- Cache `OfflineFlexilims` to increase performance. `get`, `get_children`, and other
entity lookups add to rebuild and deep-copy the whole tree on every call. Use cache
instead The cache is invalidated on `post`, `update_one`, and when reassigning
`json_file`.

Tests:
- Rewrite `tests/test_offline.py` automatically with claude to adapt to knew format

# v1.2

Features:
- Support recursive pagination in `download_database` to bypass server-side query limits of 1000 items
- Add `cross_project_entity` parameter to `get` method to allow querying entities across projects
- Modernize project configuration by switching to `pyproject.toml`
- Improve token refresh and retry logic

Bugfixes:
- Fix `OfflineFlexilims` to correctly filter entities by project in `get` method and assign `project` field in `post` method

# v1.1

Minor:
- Add `limit` parameter to `get` method

# v1.0

Major:
- Add `cross_project_entity` (default to False) in get entry point. Required for requesting entity by name or id without specifying their type.

Minor:
- Remove case warning when uploading attributes

# v0.9

- Add an `offline` mode to emulate database access from a YAML file

# v0.8

Minor:
- Remove wrong warning when status code is 200

# v0.7

- Add a `safe_execute` method to `Flexilims.Session` to token refresh. This method
  is used inside all other methods to ensure that the token is valid before
  executing the request. If the token is invalid, the method will try to refresh
  it and execute the request again. If the token cannot be refreshed, the method
  will raise an error.

# v0.6
2023-06-01

- Add `offline` module to download a JSON file version of the database
- Refactor functions useful in both online and offline mode into a `utils` module
- Create an `OffFlexilims` class to handle offline mode
- `Flexilims.Session` can be given a token at creation

# v0.5

- Add `delete` method to delete an entity
- Move password management to flexiznam as it is lab specific.

# v0.4

- Crash if uploading attribute with special characters in names and print warning when
  uploading a non-lowercase attribute

# v0.3

- Add `get_project_info` to access new end-point giving project info.
- Crash if trying to upload an attribute name with special characters

## Minor
- Raise error when setting `Flexilims.project_id` to something else than a 24
character hexadecimal string.
- Print a warning when setting an attribute name with non-lowercase characters

# v0.2

- Change how `null` values and empty structures are handled. See README.md
