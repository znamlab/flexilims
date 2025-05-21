For last release changes, see `release_notes.md`

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
