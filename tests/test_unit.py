"""Network-free unit tests for flexilims.utils and flexilims.main."""

from unittest.mock import MagicMock

import pytest

from flexilims.main import Flexilims
from flexilims.utils import FlexilimsError, check_flexilims_validity

PROJECT_ID = "606df1ac08df4d77c72c9aa4"


def _make_mock_response(status_code=200, json_data=None, text="tok", content=b"ok"):
    rep = MagicMock()
    rep.status_code = status_code
    rep.ok = 200 <= status_code < 300
    rep.text = text
    rep.content = content
    rep.json.return_value = json_data if json_data is not None else {}
    return rep


def test_check_flexilims_validity_whitespace_and_nested_keys():
    with pytest.warns(UserWarning, match="white"):
        check_flexilims_validity({"has space": 1})
    with pytest.warns(UserWarning, match="white"):
        check_flexilims_validity({"has\ttab": 1})
    with pytest.raises(FlexilimsError):
        check_flexilims_validity({"bad.key": 1})

    # Nested dict keys (e.g. filenames, hyphenated names, ints) are allowed
    nested = check_flexilims_validity(
        {"roi": {1: 2}, "cfg": {"file.tif": 1, "Cre-line": True}}
    )
    assert nested == {"roi": {1: 2}, "cfg": {"file.tif": 1, "Cre-line": True}}


def test_check_flexilims_validity_does_not_mutate_input():
    original = {"a": None, "b": (1, None), "nested": {"x": float("nan")}}
    cleaned = check_flexilims_validity(original)

    assert original["a"] is None
    assert original["b"] == (1, None)
    assert cleaned["a"] == []
    assert cleaned["b"] == [1, []]
    assert cleaned["nested"]["x"] == []


def test_online_update_validation_and_non_mutation():
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    sess.session = MagicMock()
    sess.session.put.return_value = _make_mock_response(json_data={"ok": True})
    sess.session.post.return_value = _make_mock_response(json_data={"ok": True})

    # update_one checks attribute names inside `attributes`
    with pytest.raises(FlexilimsError):
        sess.update_one(id="abc", datatype="mouse", attributes={"bad.name": 1})

    # update_many checks `update_key`
    with pytest.raises(FlexilimsError):
        sess.update_many(datatype="mouse", update_key="bad.name", update_value=1)

    # Caller's dict is not mutated by post() or update_one()
    attrs = {"nullable": None}
    sess.post(datatype="mouse", name="m1", attributes=attrs)
    assert attrs["nullable"] is None
    sess.update_one(id="abc", datatype="mouse", attributes=attrs)
    assert attrs["nullable"] is None
