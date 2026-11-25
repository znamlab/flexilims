"""Network-free unit tests for flexilims.utils and flexilims.main."""

from unittest.mock import MagicMock, patch

import pytest

from flexilims.main import DEFAULT_TIMEOUT, Flexilims, get_token, parse_error
from flexilims.utils import (
    AuthenticationError,
    FlexilimsError,
    check_flexilims_validity,
    format_results,
)

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


def test_check_flexilims_validity_replaces_nan_in_lists():
    cleaned = check_flexilims_validity(
        {"vals": [1.0, float("nan")], "nested": [[float("nan"), None]]}
    )
    assert cleaned["vals"] == [1.0, []]
    assert cleaned["nested"] == [[[], []]]


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


def test_requests_pass_timeout():
    with patch("flexilims.main.requests.post") as mock_post:
        mock_post.return_value = _make_mock_response(status_code=200, text="my_tok")
        get_token("user", "pw", timeout=12)
        assert mock_post.call_args.kwargs["timeout"] == 12

    sess = Flexilims(
        "user",
        "pw",
        project_id=PROJECT_ID,
        token={"Authorization": "Bearer tok"},
        timeout=30,
    )
    assert sess.timeout == 30
    sess.session = MagicMock()
    sess.session.get.return_value = _make_mock_response(json_data=[])
    sess.get(datatype="mouse")
    assert sess.session.get.call_args.kwargs["timeout"] == 30

    default_sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    assert default_sess.timeout == DEFAULT_TIMEOUT


def test_wrong_password_fails_fast_in_update_token():
    sess = Flexilims(
        "user", "wrong_pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    with patch("flexilims.main.requests.post") as mock_post:
        with patch("flexilims.main.time.sleep") as mock_sleep:
            mock_post.return_value = _make_mock_response(status_code=403)
            with pytest.raises(AuthenticationError):
                sess.update_token()
            assert mock_post.call_count == 1
            mock_sleep.assert_not_called()


@pytest.mark.parametrize("status_code", [401, 403])
def test_safe_execute_refreshes_token_on_401_and_403(status_code):
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer old"}
    )
    sess.session = MagicMock()
    sess.session.get.side_effect = [
        _make_mock_response(status_code=status_code),
        _make_mock_response(status_code=200, json_data=[{"id": "1"}]),
    ]
    with patch.object(sess, "update_token") as mock_refresh:
        res = sess.get(datatype="mouse")
    assert res == [{"id": "1"}]
    mock_refresh.assert_called_once()


def test_format_results_does_not_mutate_input():
    results = [{"id": "1", "name": "m1", "attributes": {"a": 10}}]
    df1 = format_results(results)
    df2 = format_results(results)
    assert results == [{"id": "1", "name": "m1", "attributes": {"a": 10}}]
    assert df1.equals(df2)
    assert df1.loc[0, "a"] == 10


def test_parse_error_multiline_html():
    html = (
        "<html>\n<body>\n<p><b>Type</b> Status Report</p>"
        "<p><b>Message</b> line1\nline2</p>"
        "<p><b>Description</b> desc</p>\n</body></html>"
    )
    parsed = parse_error(html)
    assert parsed["type"].strip() == "Status Report"
    assert "line1\nline2" in parsed["message"]
    assert parsed["description"].strip() == "desc"


def test_handle_error_404_url_and_non_200_ok():
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    rep_404 = _make_mock_response(status_code=404)
    rep_404.url = "https://example.org/flexilims/api/delete?id=123"
    with pytest.raises(IOError, match="delete\\?id=123"):
        sess.handle_error(rep_404)

    rep_204 = _make_mock_response(status_code=204)
    sess.session = MagicMock()
    sess.session.delete.return_value = rep_204
    with pytest.warns(UserWarning, match="unknown status code 204"):
        res = sess.delete("123")
    assert res is rep_204


def test_update_token_respects_wall_clock_timeout():
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    now = [0.0]

    def fake_monotonic():
        return now[0]

    def slow_fail(*args, **kwargs):
        now[0] += 60.0
        raise IOError("server timeout")

    with patch("flexilims.main.time.monotonic", side_effect=fake_monotonic):
        with patch("flexilims.main.time.sleep") as mock_sleep:
            with patch("flexilims.main.get_token", side_effect=slow_fail) as mock_get:
                with pytest.raises(IOError, match="Timeout reached"):
                    sess.update_token(timeout=100)
    # 2 attempts * 60s = 120s >= 100s deadline (not 20 attempts)
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1


def test_get_passes_offset_and_limit():
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    sess.session = MagicMock()
    sess.session.get.return_value = _make_mock_response(json_data=[])

    sess.get(datatype="session", limit=50, offset=100)
    params = sess.session.get.call_args.kwargs["params"]
    assert params["limit"] == 50
    assert params["offset"] == 100

    sess.get(datatype="session")
    params_default = sess.session.get.call_args.kwargs["params"]
    assert "limit" not in params_default
    assert "offset" not in params_default


def test_delete_by_id_and_by_origin_name():
    sess = Flexilims(
        "user", "pw", project_id=PROJECT_ID, token={"Authorization": "Bearer tok"}
    )
    sess.session = MagicMock()
    sess.session.delete.return_value = _make_mock_response(
        content=b"deleted successfully 1"
    )

    # Option A: delete by id
    assert sess.delete("abc123") == "deleted successfully 1"
    assert sess.session.delete.call_args.kwargs["params"] == {"id": "abc123"}

    # Option B: delete by datatype + origin_name (uses session project_id)
    assert (
        sess.delete(datatype="recording", origin_name="sess_1")
        == "deleted successfully 1"
    )
    assert sess.session.delete.call_args.kwargs["params"] == {
        "project_id": PROJECT_ID,
        "type": "recording",
        "origin_name": "sess_1",
    }

    # Explicit project_id overrides session default
    other_proj = "610989f9a651ff0b6237e0f6"
    sess.delete(datatype="dataset", origin_name="rec_1", project_id=other_proj)
    assert sess.session.delete.call_args.kwargs["params"] == {
        "project_id": other_proj,
        "type": "dataset",
        "origin_name": "rec_1",
    }

    # Validation errors
    with pytest.raises(ValueError, match="not both"):
        sess.delete(id="abc123", datatype="recording", origin_name="sess_1")
    with pytest.raises(ValueError, match="not both"):
        sess.delete(id="abc123", project_id=PROJECT_ID)
    with pytest.raises(ValueError, match="either"):
        sess.delete()
    with pytest.raises(ValueError, match="either"):
        sess.delete(datatype="recording")
    for bad_kwargs in (
        {"id": ""},
        {"id": "   "},
        {"datatype": "", "origin_name": "sess_1"},
        {"datatype": "recording", "origin_name": ""},
        {"datatype": "recording", "origin_name": "   "},
        {"datatype": "recording", "origin_name": "sess_1", "project_id": ""},
    ):
        with pytest.raises(ValueError, match="non-empty"):
            sess.delete(**bad_kwargs)

    sess_no_proj = Flexilims(
        "user", "pw", project_id=None, token={"Authorization": "Bearer tok"}
    )
    with pytest.raises(ValueError, match="project_id"):
        sess_no_proj.delete(datatype="recording", origin_name="sess_1")
