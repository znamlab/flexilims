from pathlib import Path
from flexiznam.config.config_tools import get_password
from flexilims import main
import flexilims.offline as flm
import pytest
import json
import datetime

BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"
USERNAME = "blota"
password = get_password(username=USERNAME, app="flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"
JSON_FILE = Path(__file__).parent / "test_data.json"


# @pytest.mark.slow
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

    reloaded_data = json.load(open(tmp_path / "test.json"), Loader=json.SafeLoader)
    assert reloaded_data == json_data

    def test_origin(parent):
        for child in parent["children"].values():
            assert child["origin_id"] == parent["id"]
            test_origin(child)

    test_origin(json_data["test_mouse"])


def test_token():
    tok = flm.get_token(USERNAME, password)
    assert len(tok)
    assert tok == "OFFLINE"


def test_update_token(tmp_path):
    with open(tmp_path / "test.json", "w") as f:
        json.dump({}, f)
    sess = flm.OfflineFlexilims(json_file=tmp_path / "test.json")
    ori_tok = sess.session.headers["Authorization"]
    # just check that it does not crash. The function does not do anythin
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


def test_get_req():
    sess = flm.OfflineFlexilims(JSON_FILE)
    # basic test
    sess.get(datatype="session", project_id=PROJECT_ID)
    r = sess.get(datatype="recording", project_id=PROJECT_ID)
    assert len(r) >= 1
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


def test_get_project_info():
    sess = flm.OfflineFlexilims(JSON_FILE)
    from flexilims.utils import FlexilimsError

    with pytest.raises(FlexilimsError):
        sess.get_project_info()


def test__find_entity():
    sess = flm.OfflineFlexilims(JSON_FILE)
    mouse = sess._find_entity(MOUSE_ID)
    assert mouse["name"] == "test_mouse"
    assert mouse["id"] == MOUSE_ID
    assert id(mouse) == id(sess._json_data["test_mouse"])


def test_update_one():
    # test without project_id
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
    rep = sess.update_one(
        id=entity_id,
        datatype="recording",
        strict_validation=False,
        allow_nulls=False,
        attributes=dict(
            nested=dict(level="new_test"), list=["a", 1], number=12, nan="NaN", empty=""
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

    assert rep["attributes"]["nan"] == None
    assert rep["attributes"]["number"] == None
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
    # update origin_id only
    rep = sess.update_one(
        id=entity_id, origin_id=MOUSE_ID, datatype="recording", strict_validation=False
    )
    assert rep["origin_id"] == MOUSE_ID
    # put back original id
    rep = sess.update_one(
        id=entity_id, origin_id=orid, datatype="recording", strict_validation=False
    )
    assert rep["origin_id"] == orid

    # Update the file
    sess2 = flm.OfflineFlexilims(JSON_FILE, edit_file=True)
    original = sess2.get(datatype="recording", name="test_recording")[0]
    sess2.update_one(id=original["id"], attributes=dict(test_write="written"))
    with open(JSON_FILE, "r") as f:
        txt = f.read()
    assert "test_write: written" in txt
    sess.update_one(id=original["id"], attributes=dict(test_write="original"))
    with open(JSON_FILE, "r") as f:
        txt = f.read()
    assert "test_write: written" in txt
    sess2.update_one(id=original["id"], attributes=dict(test_write="original"))
    with open(JSON_FILE, "r") as f:
        txt = f.read()
    assert "test_write: original" in txt
    sess2 = flm.OfflineFlexilims(JSON_FILE)
    for i, k in enumerate(sess._flat_data()):
        if k["name"] != original["name"]:
            assert sess2._flat_data()[i] == k


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
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(
            path="none", empty="", none=None, nan=float("nan"), null="null"
        ),
        strict_validation=False,
    )
    assert rep["attributes"]["empty"] == ""
    assert rep["attributes"]["none"] == None


if __name__ == "__main__":
    test_post_null()
    test_update_one()
    test_post_req()
    test__find_entity()
    test_get_req()
    test_get_children()
