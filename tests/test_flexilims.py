"""Unit tests for the main flexilims wrappers"""
import json

import pytest
import datetime
import numpy as np
import flexilims as flm
from flexilims.main import FlexilimsError
from flexiznam.config.config_tools import get_password

BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"
USERNAME = "blota"
password = get_password(username=USERNAME, app="flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"


def test_token():
    tok = flm.get_token(USERNAME, password)
    assert len(tok)


def test_session_creation():
    sess = flm.Flexilims(USERNAME, password)
    assert sess.project_id is None
    sess.project_id = PROJECT_ID
    sess = flm.Flexilims(USERNAME, password, project_id=PROJECT_ID)
    assert sess.project_id == PROJECT_ID
    old_token = sess.session.headers["Authorization"].split(" ")[1]
    tok = flm.get_token(USERNAME, password)
    sess = flm.Flexilims(USERNAME, password, token=tok)
    assert sess.session.headers["Authorization"] != old_token
    assert sess.session.headers["Authorization"] == tok["Authorization"]


def test_unvalid_request():
    sess = flm.Flexilims(USERNAME, password)
    rep = sess.session.get(
        sess.base_url + "get",
        params=dict(type="recording", randomstuff="randomtext", project_id=PROJECT_ID),
    )
    assert rep.status_code == 400
    err = flm.main.parse_error(rep.content)
    get_valid_fields = (
        "[type, name, origin_id, project_id, attributes, "
        "custom_entities, id, date_created, created_by, "
        "date_created_operator, query_key, query_value, "
        "strict_validation, allow_nulls, external_resource]"
    )
    err_msg = " randomstuff is not valid. Valid fields are "
    assert err["message"] == err_msg + get_valid_fields


def test_get_req():
    sess = flm.Flexilims(USERNAME, password, base_url=BASE_URL)
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


def test_get_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype="InvalidType", project_id=PROJECT_ID)
    assert exc_info.value.args[0] == "Error 400:  type InvalidType is not defined"
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype="session", project_id="NotAProject")
    assert (
        exc_info.value.args[0] == "Error 400:  project_id not valid, please provide "
        "a valid hexadecimal value"
    )
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype="session", project_id=PROJECT_ID, id="unvalid")
    assert (
        exc_info.value.args[0] == "Error 400:  please provide a valid hexadecimal "
        "value for id"
    )


def test_get_children():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    ch = sess.get_children(id=MOUSE_ID)
    assert len(ch) >= 1
    assert "test_session" in [c["name"] for c in ch]


def test_get_children_error():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    with pytest.raises(OSError) as exc_info:
        sess.get_children(id="unvalid_id")
    assert (
        exc_info.value.args[0] == "Error 400:  id not valid, please provide a "
        "hexadecimal value"
    )


def test_get_project_info():
    sess = flm.Flexilims(USERNAME, password=password)
    pj = sess.get_project_info()
    assert isinstance(pj, list)
    assert len(pj) > 1
    assert all(["uuid" in p for p in pj])


def test_update_one_errors():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    with pytest.raises(OSError) as exc_info:
        sess.update_one(id=MOUSE_ID, datatype="mouse", attributes=dict(camel="humpy"))
    assert (
        exc_info.value.args[0] == "Error 400:  Update failed. &#39;note&#39; is not "
        "defined in lab settings. If you have "
        "&#39;null&#39; values please substitute (null) "
        "with empty string (&#39;&#39;) "
    )
    # Even without strict validation, setting an attribute outside of valid values fails
    recs = sess.get("recording")
    with pytest.raises(OSError) as exc_info:
        sess.update_one(
            id=recs[0]["id"],
            datatype="recording",
            attributes=dict(recording_type="humpy"),
            strict_validation=False,
        )
    assert (
        exc_info.value.args[0] == "Error 400:  Update failed. &#39;humpy&#39; is not"
        " a valid value for recording_type. If you have"
        " &#39;null&#39; values please substitute (null)"
        " with empty string (&#39;&#39;) "
    )
    with pytest.raises(OSError) as exc_info:
        sess.update_one(
            id=recs[0]["id"],
            name="test_recording",
            datatype="recording",
            strict_validation=False,
        )
    assert exc_info.value.args[0] == (
        "Error 400:  Update failed. Check sample name. "
        "Sample test_recording already exist in the "
        "project test. If you have &#39;null&#39; values "
        "please substitute (null) with empty string ("
        "&#39;&#39;) "
    )
    with pytest.raises(OSError) as exc_info:
        sess.update_one(
            id=recs[0]["id"],
            origin_id="randomness",
            datatype="recording",
            strict_validation=False,
        )
    assert exc_info.value.args[0] == (
        "Error 400:  please provide a " "valid hexadecimal value for origin_id"
    )


def test_update_one():
    # test without project_id
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    original = sess.get(datatype="recording", name="test_recording")[0]

    orid = original["origin_id"]
    entity_id = original["id"]
    # update nothing
    rep = sess.update_one(id=entity_id, datatype="recording", strict_validation=False)
    assert rep == original
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
    assert get["listofdict"][1][0] is None
    assert get["listofdict"][2][1] is None
    assert get["listofdict"][3]["t"][0] is None
    assert get["listofdict"][3]["t"][1][0] is None

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

    assert rep["attributes"]["nan"] == ""
    assert rep["attributes"]["number"] == ""
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


def test_update_many_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    # get to know how many session there are
    n_sess = len(sess.get(datatype="session"))
    rep = sess.update_many(
        datatype="session",
        update_key="test_attribute",
        update_value="new_value",
        query_key=None,
        query_value=None,
    )
    assert rep == (
        "updated successfully %d items of type session with "
        "test_attribute=new_value" % n_sess
    )
    rep = sess.update_many(
        datatype="session",
        update_key="test_attribute",
        update_value="new_value",
        query_key="test_uniq",
        query_value="nonexistingvalue",
    )
    assert (
        rep == "updated successfully 0 items of type session with"
        " test_attribute=new_value"
    )
    rep = sess.update_many(
        datatype="session",
        query_key="test_uniq",
        query_value="unique",
        update_key="test_uniq",
        update_value="unique",
    )
    assert rep == "updated successfully 1 items of type session with test_uniq=unique"
    rep = sess.update_many(
        datatype="dataset",
        query_key="path",
        query_value="unique/fake/path",
        update_key="is_raw",
        update_value="yes",
    )
    assert rep == "updated successfully 0 items of type dataset with is_raw=yes"


def test_post_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
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
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(
            path="none", empty="", none=None, nan=float("nan"), null="null"
        ),
        strict_validation=False,
    )


def test_post_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(IOError):
        sess.post(
            datatype="recording",
            name="randomname",
            project_id=PROJECT_ID,
            attributes=dict(random_attribute="should fail"),
        )

    with pytest.raises(AssertionError):
        sess.post(datatype="mouse", project_id=None, name="temp", attributes={})
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="NotAType", project_id=PROJECT_ID, name="temp", attributes={}
        )
    assert exc_info.value.args[0] == "Error 400:  type provided is not defined"
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="mouse", project_id="InvalidProject", name="temp", attributes={}
        )
    assert exc_info.value.args[0] == (
        "Error 400:  please provide a valid hexadecimal " "value for project_id"
    )
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="recording",
            project_id=PROJECT_ID,
            name="test_ran_on_%s_with_origin" % "now",
            attributes=dict(rec=10),
            origin_id="605a36c53b38df2abd7757e9",
            other_relations="undefined",
        )
    err_msg = (
        "Error 400:  other_relations is not valid. Valid fields are [type, name, "
        "origin_id, project_id, attributes, custom_entities, id, date_created, "
        "created_by, date_created_operator, query_key, query_value, "
        "strict_validation, allow_nulls, external_resource]"
    )
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="recording",
            project_id=PROJECT_ID,
            name="test_ran_on_%s_with_origin" % "now",
            attributes=dict(rec=10),
            origin_id="605a36c53b38df2abd7757e9",
        )
    assert exc_info.value.args[0] == "Error 400:  origin not found"
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="recording",
            project_id=PROJECT_ID,
            name="test_ran_on_%s_with_origin" % "now",
            attributes=dict(rec=10),
            origin_id=MOUSE_ID,
        )
    err_msg = (
        "Error 400:  Save failed. &#39;rec&#39; is not defined in lab settings. "
        "If you have &#39;null&#39; values please substitute (null) with empty "
        "string (&#39;&#39;) "
    )
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="dataset", project_id=PROJECT_ID, name="suite2p", attributes=dict()
        )
    err_msg = (
        "Error 400:  Save failed. &#39;path&#39; is a necessary attribute for "
        "dataset. If you have &#39;null&#39; values please substitute (null) "
        "with empty string (&#39;&#39;) "
    )
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(
            datatype="dataset",
            project_id=PROJECT_ID,
            name="suite2prandom",
            attributes=dict(datatype="camOra"),
        )
    err_msg = (
        "Error 400:  Save failed. &#39;datatype&#39; is not defined in lab "
        "settings. If you have &#39;null&#39; values please substitute (null) "
        "with empty string (&#39;&#39;) "
    )
    assert exc_info.value.args[0] == err_msg
    json_error = dict(
        set={1, 2},
        complex=complex(1, 1),
        frozenset=frozenset({1}),
        bytes=bytes(0),
        array=np.arange(10),
    )
    for k, v in json_error.items():
        with pytest.raises(TypeError):
            sess.post(
                datatype="dataset",
                project_id=PROJECT_ID,
                name="random",
                attributes=dict(k=v, path="p"),
            )

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for bad_attr in ("plu+s", "I can't", ",", ".", "2**2"):
        with pytest.raises(FlexilimsError):
            sess.post(
                datatype="session",
                name="test_ran_on_%s" % now,
                attributes={bad_attr: "fine+value", "path": "o"},
                project_id=PROJECT_ID,
                strict_validation=False,
            )


def test_delete():
    sess = flm.Flexilims(USERNAME, password, project_id=PROJECT_ID)
    # post something to delete it
    rep = sess.get(datatype="recording", name="rec_to_delete")
    if rep:
        rep = rep[0]
    else:
        rep = sess.post(
            datatype="recording", name="rec_to_delete", attributes=dict(path="temp")
        )
    assert sess.get(datatype="recording", id=rep["id"])
    dlm = sess.delete(rep["id"])
    assert dlm.startswith("deleted successfully")
    assert not sess.get(datatype="recording", id=rep["id"])
    with pytest.raises(OSError):
        sess.delete(rep["id"])
