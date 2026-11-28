# Unreleased

Changes:
- Remove the obsolete whitespace `UserWarning` from `check_flexilims_validity` (attribute names containing spaces are supported by both the FlexiLIMS API and Web UI).

Minor:
- Fix the `ptest` typo (should be `pytest`) in the uv `dev` dependency group, add `numpy` to it, remove the outdated `dev` optional-dependency extra, and make tox install the `dev` dependency group instead.
- Run ruff and ty pre-commit hooks from the project's uv environment (replacing the pinned ruff-pre-commit and mypy hooks); bump ruff to 0.17.6 and ty to 0.0.112, and add pre-commit to the uv `dev` group.
- Offline duplicate-name errors (`post` and renaming via `update_one`) now raise `NameNotUniqueError`, a subclass of both `FlexilimsError` and `IOError`, with a message matching the online API (`... already exist in the project ...`), so callers such as flexiznam handle name conflicts the same way online and offline.

# v26.11.0

Features:
- Support deleting direct children by type and origin name in `Flexilims.delete()` via
`delete(datatype=..., origin_name=..., project_id=...)` (non-recursive).
- Add `offset` pagination parameter to `Flexilims.get()` and `OfflineFlexilims.get()`,
and switch `download_database()` to paginate with `offset` + `limit=1000` instead of
`date_created`.
- Add `limit`, `cross_project_entity`, and multi-attribute `query_key`/`query_value`
support to `OfflineFlexilims.get()` for parity with online `Flexilims.get()`.
- Add configurable request timeouts (`timeout=60` by default) to `Flexilims` and
`get_token` so stalled requests no longer hang indefinitely.

Breaking changes & deprecations:
- Remove the server-rejected `other_relations` parameter from `post()` (online and
offline).
- Deprecate the unused `project_id` parameter in `update_one()` (emits
`DeprecationWarning` if passed).

Bugfixes:
- Fix attribute validation in `check_flexilims_validity`: use regex whitespace matching,
return a cleaned deep copy instead of mutating caller dicts in place, replace `NaN`
inside lists in `_cleanlist`, and validate `attributes` in `update_one` and `update_key`
in `update_many`.
- Stop mutating caller dicts in place in `format_results`.
- Fail immediately on HTTP 401/403 credential errors in `get_token` instead of retrying
for 10 minutes in `update_token`, use wall-clock deadlines in `update_token`, and
refresh expired tokens on both 401 and 403.
- Return non-200 2xx responses from `safe_execute` as warned, report the actual request
URL on 404, pass `strict_validation` via `params` in `post()` and `update_many()`, and
make `parse_error` handle multiline HTML error pages.
- Fix `OfflineFlexilims` data integrity and return types: enforce name uniqueness and
validate `origin_id` in `post`, raise `FlexilimsError` on unknown `id` in `update_one`
and `get_children`, re-key renamed entities safely, forward `allow_nulls`/`allow_strings`
to nested dicts, filter `get()` directly in Python (returning deep-copied `list[dict]`
with `origin_id=None` for root entities), and set `"origin_id": None` on posted roots.
- Deduplicate paginated results in `download_database`, keep root `origin_id` as `None`,
guard against infinite pagination loops, and log a warning when orphaned entities (and
their descendants) are omitted.

Tests & Tooling:
- Add network-free unit tests in `tests/test_unit.py` and expanded offline/live
regression tests in `tests/test_offline.py`, `tests/test_main_client.py`, and
`tests/test_flexilims.py`.
- Add `AGENTS.md` with changelog, git confirmation, and development check guidelines.

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
