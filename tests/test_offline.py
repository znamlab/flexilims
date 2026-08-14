import datetime
import json
import os
import shutil
from importlib import import_module
from pathlib import Path

import pytest

try:
    get_password = import_module("flexiznam.config.config_tools").get_password
except ImportError:
    print("Flexiznam is not installed")
    get_password = None

import flexilims.offline as flm
from flexilims import main
from flexilims.utils import FlexilimsError

BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"
USERNAME = "blota"
if get_password is None:
    password = "NotDefined"
else:
    password = get_password(username=USERNAME, app="flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"
JSON_FILE = Path(__file__).parent / "test_data.json"
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture
def json_copy(tmp_path):
    """A private copy of the fixture data, safe for tests to mutate/persist to."""
    target = tmp_path / "test_data.json"
    shutil.copy(JSON_FILE, target)
    return target


def _load_json(path):
    with open(path) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# download_database
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    IN_GITHUB_ACTIONS or get_password is None,
    reason="Test requires the Crick network and flexiznam credentials.",
)
def test_download_database(tmp_path):
    from flexilims.offline import download_database

    flm_sess = main.Flexilims(USERNAME, password, PROJECT_ID)
    json_data = download_database(
        flm_sess, types=("mouse", "session", "recording", "dataset"), verbose=True
    )
    assert isinstance(json_data, dict)
    assert len(json_data) == 1
    assert next(iter(json_data)) == "test_mouse"
    ts = json_data["test_mouse"]["children"]["test_session"]
    assert "test_recording" in ts["children"]

    with open(tmp_path / "test.json", "w") as f:
        json.dump(json_data, f)

    reloaded_data = json.load(open(tmp_path / "test.json"))

    def test_rec(dict_a, dict_b, num_diff=0):
        """Recursively test that dict are identitical and print keys that are not"""
        for k, v in dict_a.items():
            assert k in dict_b
            if k == "origin_id":
                continue
            elif isinstance(v, dict):
                test_rec(v, dict_b[k], num_diff)
            elif v != dict_b[k]:
                print(k)
                print(type(v), type(dict_b[k]))
                num_diff += 1
        return num_diff

    num_diff = test_rec(json_data, reloaded_data)
    assert num_diff == 0


def test_download_database_pagination():
    from flexilims.offline import download_database

    class MockFlexilimsSession:
        def __init__(self):
            # Create a list of 2500 mock datasets, with incremental dateCreated
            self.mock_data = []
            for i in range(2500):
                self.mock_data.append(
                    {
                        "id": f"ds_{i}",
                        "type": "dataset",
                        "name": f"dataset_{i}",
                        "dateCreated": 1000000 + i,
                        "origin_id": "rec_1",
                    }
                )
            # Also add a parent mouse, session, recording
            self.mock_data.append(
                {
                    "id": "mouse_1",
                    "type": "mouse",
                    "name": "test_mouse",
                    "origin_id": None,
                }
            )
            self.mock_data.append(
                {
                    "id": "sess_1",
                    "type": "session",
                    "name": "test_session",
                    "origin_id": "mouse_1",
                }
            )
            self.mock_data.append(
                {
                    "id": "rec_1",
                    "type": "recording",
                    "name": "test_recording",
                    "origin_id": "sess_1",
                }
            )

        def get(self, datatype, date_created=None, date_created_operator="gt"):
            # Filter the mock data by datatype
            items = [item for item in self.mock_data if item["type"] == datatype]
            if date_created is not None:
                if date_created_operator == "gt":
                    items = [
                        item for item in items if item["dateCreated"] > date_created
                    ]
                elif date_created_operator == "lt":
                    items = [
                        item for item in items if item["dateCreated"] < date_created
                    ]
            # Enforce the server pagination limit of 1000
            return items[:1000]

    mock_sess = MockFlexilimsSession()
    json_data = download_database(
        mock_sess, types=("mouse", "session", "recording", "dataset"), verbose=False
    )

    # Check that test_mouse was created at root
    assert "test_mouse" in json_data
    # Check that datasets were recursively added down the hierarchy
    sess_node = json_data["test_mouse"]["children"]["test_session"]
    rec_node = sess_node["children"]["test_recording"]
    assert "children" in rec_node
    # There should be exactly 2500 children datasets!
    assert len(rec_node["children"]) == 2500


# --------------------------------------------------------------------------- #
# Session creation / misc
# --------------------------------------------------------------------------- #


def test_token():
    tok = flm.get_token(USERNAME, password)
    assert len(tok)
    assert tok == "OFFLINE"


def test_update_token(tmp_path):
    with open(tmp_path / "test.json", "w") as f:
        json.dump({}, f)
    sess = flm.OfflineFlexilims(json_file=tmp_path / "test.json")
    sess.session.headers["Authorization"]
    # just check that it does not crash. The function does not do anything
    sess.update_token()


def test_session_creation(tmp_path):
    json_file = tmp_path / "test.json"
    with open(json_file, "w") as f:
        json.dump({}, f)
    sess = flm.OfflineFlexilims(json_file)
    assert sess.project_id is None
    sess.project_id = PROJECT_ID
    sess = flm.OfflineFlexilims(json_file, project_id=PROJECT_ID)
    assert sess.project_id == PROJECT_ID


def test_get_project_info():
    sess = flm.OfflineFlexilims(JSON_FILE)
    with pytest.raises(FlexilimsError):
        sess.get_project_info()


# --------------------------------------------------------------------------- #
# get / get_children / _find_entity
# --------------------------------------------------------------------------- #


def test_get_req():
    sess = flm.OfflineFlexilims(JSON_FILE)
    # basic test
    sess.get(datatype="session", project_id=PROJECT_ID)
    r = sess.get(datatype="recording", project_id=PROJECT_ID)
    assert len(r) >= 1
    # test project filtering: should find nothing if filtered by a different project ID
    r_wrong_project = sess.get(datatype="recording", project_id="different_project_id")
    assert len(r_wrong_project) == 0
    # test session default project_id
    sess_with_project = flm.OfflineFlexilims(JSON_FILE, project_id=PROJECT_ID)
    assert len(sess_with_project.get(datatype="recording")) >= 1
    sess_with_wrong_project = flm.OfflineFlexilims(
        JSON_FILE, project_id="different_project_id"
    )
    assert len(sess_with_wrong_project.get(datatype="recording")) == 0

    # test all filtering arguments:
    r = sess.get(
        datatype="recording",
        project_id=PROJECT_ID,
        query_key="rec_attr",
        query_value="attribute of recording",
    )
    assert len(r) == 1
    r = sess.get(datatype="dataset", project_id=PROJECT_ID, id=MOUSE_ID)
    assert len(r) == 0
    r = sess.get(datatype="dataset", project_id=PROJECT_ID, name="MOUSE_ID")
    assert len(r) == 0
    r = sess.get(datatype="mouse", project_id=PROJECT_ID, id=MOUSE_ID)
    assert len(r) == 1
    r = sess.get(datatype="dataset", project_id=PROJECT_ID, created_by="Antonin Blot")
    assert len(r) >= 1
    cutoff = 1620897685816
    r = sess.get(
        datatype="dataset",
        project_id=PROJECT_ID,
        date_created=cutoff,
        date_created_operator="gt",
    )
    r2 = sess.get(datatype="dataset", project_id=PROJECT_ID, date_created=cutoff)
    assert (len(r) == len(r2)) and all([el in r2 for el in r])
    assert all(el["dateCreated"] >= cutoff for el in r)
    r = sess.get(
        datatype="dataset",
        project_id=PROJECT_ID,
        date_created=cutoff,
        date_created_operator="lt",
    )
    assert all(el["dateCreated"] <= cutoff for el in r)
    r = sess.get(datatype="dataset", project_id=PROJECT_ID, name="test_dataset")
    assert (len(r) == 1) and (r[0]["name"] == "test_dataset")
    # test getting by name with no datatype
    r = sess.get(project_id=PROJECT_ID, name="test_dataset")
    assert (len(r) == 1) and (r[0]["name"] == "test_dataset")


def test_get_children():
    sess = flm.OfflineFlexilims(JSON_FILE)
    ch = sess.get_children(id=MOUSE_ID)
    assert len(ch) >= 1
    assert "test_session" in [c["name"] for c in ch]


def test_find_entity():
    sess = flm.OfflineFlexilims(JSON_FILE)
    mouse = sess._find_entity(MOUSE_ID)
    assert mouse["name"] == "test_mouse"
    assert mouse["id"] == MOUSE_ID
    # _find_entity must return a live reference into _json_data, not a copy,
    # since update_one mutates the object it returns in place.
    assert id(mouse) == id(sess._json_data["test_mouse"])
    assert sess._find_entity("not_a_real_id") is None


# --------------------------------------------------------------------------- #
# Caching: _flat_data / _find_entity results are cached until data changes
# --------------------------------------------------------------------------- #


def test_flat_data_is_cached():
    sess = flm.OfflineFlexilims(JSON_FILE)
    first = sess._flat_data()
    second = sess._flat_data()
    assert first is second, "_flat_data should return the cached list, not rebuild it"

    first_wc = sess._flat_data(keep_children=True)
    second_wc = sess._flat_data(keep_children=True)
    assert first_wc is second_wc
    # the two variants (with/without children) are cached independently
    assert first is not first_wc


def test_find_entity_index_is_built_once():
    sess = flm.OfflineFlexilims(JSON_FILE)
    assert sess._entity_index is None
    mouse = sess._find_entity(MOUSE_ID)
    index = sess._entity_index
    assert index is not None
    again = sess._find_entity(MOUSE_ID)
    assert sess._entity_index is index, "index should not be rebuilt on a second call"
    assert again is mouse


def test_cache_invalidated_on_json_file_reload(json_copy):
    sess = flm.OfflineFlexilims(json_copy)
    cached = sess._flat_data()
    sess._find_entity(MOUSE_ID)
    assert sess._entity_index is not None

    # reassigning json_file reloads from disk and must reset every cache
    sess.json_file = sess.json_file
    assert sess._flat_cache is None
    assert sess._flat_cache_with_children is None
    assert sess._entity_index is None

    refreshed = sess._flat_data()
    assert refreshed == cached
    assert refreshed is not cached


def test_cache_invalidated_by_update_one():
    sess = flm.OfflineFlexilims(JSON_FILE)
    cached = sess._flat_data()

    sess.update_one(
        id=MOUSE_ID, attributes=dict(animal_name="Tom"), strict_validation=False
    )
    assert sess._flat_cache is None
    assert sess._flat_cache_with_children is None

    refreshed = sess._flat_data()
    assert refreshed is not cached
    updated = [el for el in refreshed if el["id"] == MOUSE_ID][0]
    assert updated["attributes"]["animal_name"] == "Tom"


def test_cache_invalidated_by_post():
    sess = flm.OfflineFlexilims(JSON_FILE)
    cached_flat = sess._flat_data()
    sess._find_entity(MOUSE_ID)
    assert sess._entity_index is not None

    new_entity = sess.post(
        datatype="session", name="cache_invalidation_test", attributes=dict(path="x")
    )
    assert sess._flat_cache is None
    assert sess._entity_index is None

    refreshed = sess._flat_data()
    assert refreshed is not cached_flat
    assert any(el["id"] == new_entity["id"] for el in refreshed)
    assert sess._find_entity(new_entity["id"]) is not None


# --------------------------------------------------------------------------- #
# update_one
# --------------------------------------------------------------------------- #


def test_update_one():
    sess = flm.OfflineFlexilims(JSON_FILE)
    original = sess.get(datatype="recording", name="test_recording")[0]
    ori_data = sess._find_entity(original["id"])

    orid = original.get("origin_id", None)
    entity_id = original["id"]
    # update nothing
    rep = sess.update_one(id=entity_id, datatype="recording", strict_validation=False)
    assert rep == ori_data
    # update attributes
    rep = sess.update_one(
        id=entity_id,
        datatype="recording",
        strict_validation=False,
        attributes=dict(test_uniq="new_test"),
    )
    assert rep["attributes"]["test_uniq"] == "new_test"

    # lists are only partially supported offline and should warn
    with pytest.warns(UserWarning, match="Updating list"):
        rep = sess.update_one(
            id=entity_id,
            datatype="recording",
            strict_validation=False,
            allow_nulls=False,
            attributes=dict(
                nested=dict(level="new_test"),
                list=["a", 1],
                number=12,
                nan="NaN",
                empty="",
            ),
        )
    assert isinstance(rep["attributes"]["nested"], dict)
    assert rep["attributes"]["nested"]["level"] == "new_test"
    assert rep["attributes"]["nan"] == "NaN"
    assert len(rep["attributes"]["list"]) == 2
    assert isinstance(rep["attributes"]["number"], int)

    # test a weird nesting with empty structures and nones
    nested = dict(
        sublvl=dict(o=1, none=None), empty_lvl=[], list_list=[1, [], ["o", None]]
    )
    listofdict = [dict(a=2), [dict()], (1, None), (dict(t=([], (None, 1))))]
    with pytest.warns(UserWarning, match="Updating list"):
        sess.update_one(
            id=entity_id,
            datatype="recording",
            strict_validation=False,
            allow_nulls=True,
            attributes=dict(nested=nested, listofdict=listofdict),
        )
    get = sess.get(datatype="recording", id=entity_id)[0]["attributes"]
    assert isinstance(get["nested"], dict)
    assert isinstance(get["nested"]["sublvl"], dict)
    assert get["nested"]["empty_lvl"] is None
    assert get["nested"]["sublvl"]["none"] is None
    assert isinstance(get["listofdict"], list)
    for element, expected_type in zip(get["listofdict"], [dict, list, list, dict]):
        assert isinstance(element, expected_type)

    # when allow null is False, '' are ignored
    rep = sess.update_one(
        id=entity_id,
        datatype="recording",
        strict_validation=False,
        allow_nulls=False,
        attributes=dict(test_unique=21, nan=""),
    )
    assert rep["attributes"]["nan"] == "NaN"
    # When allow_nulls is True, erase
    rep = sess.update_one(
        id=entity_id,
        datatype="recording",
        strict_validation=False,
        allow_nulls=True,
        attributes=dict(number="", nan="", path="d"),
    )
    assert rep["attributes"]["nan"] is None
    assert rep["attributes"]["number"] is None

    # update name only
    rep = sess.update_one(
        id=entity_id,
        name="R101501_new_name",
        datatype="recording",
        strict_validation=False,
    )
    assert rep["name"] == "R101501_new_name"
    sess.update_one(
        id=entity_id,
        name=original["name"],
        datatype="recording",
        strict_validation=False,
    )

    # update origin_id only (this is deliberately fragile offline, hence the warning)
    with pytest.warns(UserWarning, match="origin_id"):
        rep = sess.update_one(
            id=entity_id,
            origin_id=MOUSE_ID,
            datatype="recording",
            strict_validation=False,
        )
    assert rep["origin_id"] == MOUSE_ID
    # put back original id
    with pytest.warns(UserWarning, match="origin_id"):
        rep = sess.update_one(
            id=entity_id, origin_id=orid, datatype="recording", strict_validation=False
        )
    assert rep["origin_id"] == orid

    # datatype mismatch should raise
    with pytest.raises(AssertionError):
        sess.update_one(id=entity_id, datatype="dataset", strict_validation=False)


def test_update_one_persists_to_file_only_when_editable(json_copy):
    """`edit_file` controls whether update_one writes through to disk, and
    sessions never see each other's in-memory-only changes."""
    ram_only_session = flm.OfflineFlexilims(json_copy)
    original = ram_only_session.get(datatype="recording", name="test_recording")[0]

    ram_only_session.update_one(
        id=original["id"],
        attributes=dict(test_write="ram_only"),
        strict_validation=False,
    )
    on_disk = _load_json(json_copy)
    recording_on_disk = on_disk["test_mouse"]["children"]["test_session"]["children"][
        "test_recording"
    ]
    assert "test_write" not in recording_on_disk["attributes"]

    editable_session = flm.OfflineFlexilims(json_copy, edit_file=True)
    editable_session.update_one(
        id=original["id"],
        attributes=dict(test_write="written"),
        strict_validation=False,
    )
    on_disk = _load_json(json_copy)
    recording_on_disk = on_disk["test_mouse"]["children"]["test_session"]["children"][
        "test_recording"
    ]
    assert recording_on_disk["attributes"]["test_write"] == "written"

    # a fresh session reloading the same file sees the persisted change ...
    reloaded_session = flm.OfflineFlexilims(json_copy)
    reloaded = reloaded_session.get(datatype="recording", id=original["id"])[0]
    assert reloaded["attributes"]["test_write"] == "written"

    # ... while the RAM-only session still holds its own, un-persisted value
    ram_only_current = ram_only_session.get(datatype="recording", id=original["id"])[0]
    assert ram_only_current["attributes"]["test_write"] == "ram_only"


# --------------------------------------------------------------------------- #
# post
# --------------------------------------------------------------------------- #


def test_post_req():
    sess = flm.OfflineFlexilims(JSON_FILE)
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(path="test/session"),
    )
    rep = sess.post(
        datatype="recording",
        name="test_ran_on_%s_with_origin" % now,
        attributes=dict(session=rep["id"], trial=1, path="test/session/recording"),
        origin_id=MOUSE_ID,
        strict_validation=False,
    )
    datatypes = dict(
        dataset_type="camera",
        path="random",
        int=12,
        float=12.1,
        list=[0, 1],
        tuple=(0, 1),
        dict=dict(o=2),
        bool=False,
        empty_dict=dict(),
        empty_list=[],
        empty_str="",
    )

    with pytest.warns(UserWarning, match="Updating list"):
        sess.post(
            datatype="dataset",
            name="test_ran_on_%s_dataset" % now,
            attributes=datatypes,
            origin_id=rep["id"],
            strict_validation=False,
        )
    gt = sess.get(datatype="dataset", name="test_ran_on_%s_dataset" % now)[0][
        "attributes"
    ]
    transformed = dict(tuple=[], empty_dict=None, empty_list=None)
    for k, v in gt.items():
        if k in transformed:
            expected = type(transformed[k])
        else:
            expected = type(datatypes[k])
        assert isinstance(v, expected)


def test_post_null():
    sess = flm.OfflineFlexilims(JSON_FILE)
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with pytest.warns(UserWarning, match="Updating list"):
        rep = sess.post(
            datatype="session",
            name="test_ran_on_%s" % now,
            attributes=dict(
                path="none", empty="", none=None, nan=float("nan"), null="null"
            ),
            strict_validation=False,
        )
    assert rep["attributes"]["empty"] == ""
    assert rep["attributes"]["none"] is None


def test_update_many_not_implemented():
    sess = flm.OfflineFlexilims(JSON_FILE)
    with pytest.raises(NotImplementedError):
        sess.update_many([])
