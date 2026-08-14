"""Network-free unit tests for the main Flexilims client."""

import pytest

from flexilims import main
from flexilims.utils import AuthenticationError

PROJECT_ID = "a" * 24


class FakeResponse:
    """Minimal requests response used to exercise client behavior."""

    def __init__(self, status_code=200, payload=None, content=b"", text="token"):
        self.status_code = status_code
        self.payload = payload
        self.content = content
        self.text = text
        self.ok = status_code < 400

    def json(self):
        return self.payload


class FakeSession:
    """Record request arguments and return a configured response."""

    def __init__(self, response):
        self.headers = {}
        self.response = response
        self.calls = []

    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response

    def get(self, url, **kwargs):
        return self._request("get", url, **kwargs)

    def put(self, url, **kwargs):
        return self._request("put", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("post", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request("delete", url, **kwargs)


@pytest.fixture
def client():
    return main.Flexilims(
        "user",
        "password",
        project_id=PROJECT_ID,
        token={"Authorization": "Bearer existing"},
    )


def test_get_builds_request_parameters(client):
    session = FakeSession(FakeResponse(payload=[{"id": "recording-1"}]))
    client.session = session

    result = client.get(
        datatype="recording",
        name="example",
        date_created=123,
        cross_project_entity=True,
        limit=10,
    )

    assert result == [{"id": "recording-1"}]
    assert session.calls == [
        (
            "get",
            client.base_url + "get",
            {
                "params": {
                    "type": "recording",
                    "project_id": PROJECT_ID,
                    "cross_project_entity": "yes",
                    "name": "example",
                    "date_created": 123,
                    "date_created_operator": "gt",
                    "limit": 10,
                }
            },
        )
    ]


def test_write_methods_build_expected_requests(client):
    session = FakeSession(FakeResponse(payload={"id": "created"}, content=b"updated"))
    client.session = session

    assert client.update_one("entity", "recording", name="renamed") == {"id": "created"}
    assert client.update_many("recording", "status", "done") == "updated"
    assert client.post("recording", "new", {"path": "file"}) == {"id": "created"}
    assert client.delete("entity") == "updated"

    assert session.calls == [
        (
            "put",
            client.base_url + "update-one",
            {
                "params": {
                    "type": "recording",
                    "id": "entity",
                    "strict_validation": "true",
                    "allow_nulls": "true",
                },
                "json": {"name": "renamed"},
            },
        ),
        (
            "put",
            client.base_url + "update-many",
            {
                "params": {
                    "type": "recording",
                    "project_id": PROJECT_ID,
                    "update_key": "status",
                    "update_value": "done",
                }
            },
        ),
        (
            "post",
            client.base_url + "save?strict_validation=true",
            {
                "json": {
                    "type": "recording",
                    "name": "new",
                    "project_id": PROJECT_ID,
                    "attributes": {"path": "file"},
                }
            },
        ),
        ("delete", client.base_url + "delete", {"params": {"id": "entity"}}),
    ]


def test_safe_execute_refreshes_an_expired_token(client, monkeypatch):
    responses = [FakeResponse(status_code=403), FakeResponse(payload={"ok": True})]
    refreshes = []

    def request():
        return responses.pop(0)

    monkeypatch.setattr(client, "update_token", lambda: refreshes.append(True))

    assert client.safe_execute("json", request) == {"ok": True}
    assert refreshes == [True]


@pytest.mark.parametrize(
    ("response", "exception"),
    [
        (FakeResponse(status_code=404), IOError),
        (FakeResponse(status_code=403), AuthenticationError),
        (FakeResponse(status_code=500), IOError),
    ],
)
def test_handle_error_raises_for_unsuccessful_responses(client, response, exception):
    with pytest.raises(exception):
        client.handle_error(response)


def test_parse_error_and_get_token(monkeypatch):
    message = (
        b"<b>Type</b>Bad</p><p><b>Message</b>Invalid</p>"
        b"<p><b>Description</b>Details</p>"
    )
    assert main.parse_error(message) == {
        "type": "Bad",
        "message": "Invalid",
        "description": "Details",
    }

    monkeypatch.setattr(main.requests, "post", lambda *args, **kwargs: FakeResponse())
    assert main.get_token("user", "password") == {"Authorization": "Bearer token"}
