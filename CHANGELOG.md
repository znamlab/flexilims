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