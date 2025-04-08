"""Unit tests for the main flexilims wrappers"""

import datetime

import numpy as np
import pytest
from flexiznam.config.config_tools import get_password

import flexilims as flm
from flexilims.main import FlexilimsError

TEST_URL = "http://clvd0-ws-u-t-41.thecrick.test:8080/flexilims/api/"
# BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"
USERNAME = "blota"
password = get_password(username=USERNAME, app="flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"


def test_token():
    tok = flm.get_token(USERNAME, password, base_url=TEST_URL)
    assert len(tok)


def test_update_token():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
    ori_tok = sess.session.headers["Authorization"]
    sess.update_token()
    assert sess.session.headers["Authorization"] != ori_tok


def test_session_creation():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
    assert sess.project_id is None
    sess.project_id = PROJECT_ID
    sess = flm.Flexilims(USERNAME, password, project_id=PROJECT_ID, base_url=TEST_URL)
    assert sess.project_id == PROJECT_ID
    old_token = sess.session.headers["Authorization"].split(" ")[1]
    tok = flm.get_token(USERNAME, password, base_url=TEST_URL)
    sess = flm.Flexilims(USERNAME, password, token=tok, base_url=TEST_URL)
    assert sess.session.headers["Authorization"] != old_token
    assert sess.session.headers["Authorization"] == tok["Authorization"]


def test_safe_execute():
    from flexilims.utils import AuthenticationError

    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
    rep = sess.safe_execute("json", sess.session.get, sess.base_url + "projects")
    assert len(rep) >= 1
    sess.session.headers["Authorization"] = "Bearer invalid_token"
    with pytest.raises(AuthenticationError) as exc_info:
        rep = sess.session.get(sess.base_url + "projects")
        sess.handle_error(rep)
    assert exc_info.value.args[0] == "Forbidden. Are you logged in?"
    # this does not change the token
    assert sess.session.headers["Authorization"] == "Bearer invalid_token"
    rep = sess.safe_execute("json", sess.session.get, sess.base_url + "projects")
    # this does
    assert sess.session.headers["Authorization"] != "Bearer invalid_token"


def test_unvalid_request():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
    sess.update_token()
    rep = sess.session.get(
        sess.base_url + "get",
        params=dict(type="recording", randomstuff="randomtext", project_id=PROJECT_ID),
    )
    assert rep.status_code == 400
    err = flm.main.parse_error(rep.content)
    get_valid_fields = (
        "[type, name, origin_id, custom_entity_id, project_id, attributes, "
        "custom_entities, detach_custom_entities, id, date_created, created_by, "
        "date_created_operator, query_key, query_value, "
        "strict_validation, allow_nulls, external_resource, query_value_data_type, "
        "offset, limit]"
    )
    err_msg = " randomstuff is not valid. Valid fields are "
    assert err["message"] == err_msg + get_valid_fields


def test_delete():
    sess = flm.Flexilims(USERNAME, password, project_id=PROJECT_ID, base_url=TEST_URL)
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
    assert dlm == "deleted successfully [1, 0]"
    assert not sess.get(datatype="recording", id=rep["id"])
    with pytest.raises(OSError):
        sess.delete(rep["id"])


def test_get_req():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
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
    with pytest.raises(OSError) as exc_info:
        sess.get(project_id=PROJECT_ID, name="test_dataset")
    assert exc_info.value.args[0] == "Error 400:  please specify type"
    r = sess.get(project_id=PROJECT_ID, name="test_dataset", datatype="dataset")
    assert (len(r) == 1) and (r[0]["name"] == "test_dataset")
    # It works even without the project_id
    with pytest.raises(OSError) as exc_info:
        r = sess.get(datatype="dataset", name="test_dataset")
    assert (
        exc_info.value.args[0]
        == "Error 400:  you need to provide project_id to query for dataset"
    )


def test_get_error():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
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
        sess.get(datatype="session", project_id=PROJECT_ID, id="invalid")
    assert (
        exc_info.value.args[0] == "Error 400:  please provide a valid hexadecimal "
        "value for id"
    )
    with pytest.raises(OSError) as exc_info:
        # test getting by id with no datatype
        sess.get(project_id=PROJECT_ID, id=MOUSE_ID)
    assert exc_info.value.args[0] == "Error 400:  please specify type"


def test_get_children():
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    ch = sess.get_children(id=MOUSE_ID)
    assert len(ch) >= 1
    assert "test_session" in [c["name"] for c in ch]


def test_get_children_error():
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    with pytest.raises(OSError) as exc_info:
        sess.get_children(id="unvalid_id")
    assert (
        exc_info.value.args[0] == "Error 400:  id not valid, please provide a "
        "hexadecimal value"
    )


def test_get_project_info():
    sess = flm.Flexilims(USERNAME, password=password, base_url=TEST_URL)
    pj = sess.get_project_info()
    assert isinstance(pj, list)
    assert len(pj) > 1
    assert all(["uuid" in p for p in pj])


def test_update_one_errors():
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
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
        "Error 400:  please provide a valid hexadecimal value for origin_id"
    )


def test_update_one():
    # test without project_id
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    original = sess.get(datatype="recording", name="test_recording")[0]

    orid = original["origin_id"]
    entity_id = original["id"]
    # update nothing
    rep = sess.update_one(id=entity_id, datatype="recording", strict_validation=False)
    original.pop("dateUpdated")
    rep.pop("dateUpdated")
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
    # 2025-02-15: current issue with empty strings, return error 500
    rep = sess.update_one(
        id=entity_id,
        datatype="recording",
        strict_validation=False,
        allow_nulls=False,
        attributes=dict(test_unique=21, nan="Error500", CamelCase="CamelCase"),
    )
    # assert rep["attributes"]["nan"] == "NaN"
    assert rep["attributes"]["nan"] == "Error500"
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
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
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
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        origin_id=MOUSE_ID,
        attributes=dict(path="test/session"),
    )
    assert rep["attributes"]["path"] == "test/session"
    ids = [(rep["id"], rep["type"])]
    attributes = dict(
        session=rep["id"], trial=1, CamelCase="CamelCase", path="test/session/recording"
    )
    rep = sess.post(
        datatype="recording",
        name="test_ran_on_%s_with_origin2" % now,
        attributes=attributes,
        origin_id=MOUSE_ID,
        strict_validation=False,
    )
    ids.append((rep["id"], rep["type"]))
    assert rep["attributes"] != attributes
    lower_case = {k.lower(): v for k, v in attributes.items()}
    assert rep["attributes"] == lower_case

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
    rep = sess.post(
        datatype="dataset",
        name="test_ran_on_%s_dataset" % now,
        attributes=datatypes,
        origin_id=rep["id"],
        strict_validation=False,
    )
    ids.append((rep["id"], rep["type"]))
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
    # try to keep the db a bit clean
    for i, dtype in ids:
        try:
            sess.delete(i)
        except OSError:
            # weirdly delete is sometimes recursive.
            print(f"Could not delete {dtype} {i}")
        assert not sess.get(datatype=dtype, id=i)
    print("Done")


def test_post_null():
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(
            path="none", empty="", none=None, nan=float("nan"), null="null"
        ),
        origin_id=MOUSE_ID,
        strict_validation=False,
    )
    assert rep["attributes"]["empty"] == ""
    assert rep["attributes"]["none"] == []
    # try to keep the db a bit clean
    sess.delete(rep["id"])


def test_post_error():
    sess = flm.Flexilims(USERNAME, password, base_url=TEST_URL)
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
        "Error 400:  please provide a valid hexadecimal value for project_id"
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
        "origin_id, custom_entity_id, project_id, attributes, custom_entities, "
        "detach_custom_entities, id, date_created, created_by, date_created_operator, "
        "query_key, query_value, strict_validation, allow_nulls, external_resource, "
        "query_value_data_type, offset, limit]"
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


def test_bool_attribute():
    """Adding an  updating boolean False had some issues"""
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(
            boolean_false=False,
            boolean_true=True,
            int_0=0,
            int_1=1,
            float_0=0.0,
            float_1=1.0,
            str_False="False",
            str_True="True",
            path="test/session",
        ),
        strict_validation=False,
    )
    assert rep["attributes"]["boolean_false"] == False  # noqa: E712
    assert rep["attributes"]["boolean_true"] == True  # noqa: E712
    assert rep["attributes"]["int_0"] == 0  # noqa: E712
    assert rep["attributes"]["int_1"] == 1  # noqa: E712
    # For some reason the attributes are now lowercase
    assert rep["attributes"]["str_false"] == "False"  # noqa: E712
    assert rep["attributes"]["str_true"] == "True"  # noqa: E712
    test = sess.get(datatype="session", id=rep["id"])[0]
    assert test["attributes"]["boolean_false"] == False  # noqa: E712
    assert test["attributes"]["boolean_true"] == True  # noqa: E712
    assert test["attributes"]["int_0"] == 0  # noqa: E712
    assert test["attributes"]["int_1"] == 1  # noqa: E712
    assert test["attributes"]["str_false"] == "False"  # noqa: E712
    assert test["attributes"]["str_true"] == "True"  # noqa: E712

    rep["attributes"]["str_False"] = False
    rep["attributes"]["str_True"] = True
    rep["attributes"].pop("str_false")
    rep["attributes"].pop("str_true")
    rep2 = sess.update_one(
        id=rep["id"],
        datatype="session",
        attributes=rep["attributes"],
        strict_validation=False,
    )
    assert rep2["attributes"]["str_False"] == False  # noqa: E712
    assert rep2["attributes"]["str_True"] == True  # noqa: E712
    assert rep2["attributes"]["int_0"] == 0  # noqa: E712
    assert rep2["attributes"]["int_1"] == 1  # noqa: E712
    assert rep2["attributes"]["boolean_false"] == False  # noqa: E712
    assert rep2["attributes"]["boolean_true"] == True  # noqa: E712
    # keep everything as boolean now
    rep3 = sess.update_one(
        id=rep["id"],
        datatype="session",
        attributes=dict(
            boolean_false=False,
            boolean_true=True,
            str_False=False,
            str_True=True,
            int_0=False,
            int_1=True,
            float_0=False,
            float_1=True,
        ),
        strict_validation=False,
    )
    assert rep3["attributes"]["str_False"] == False  # noqa: E712
    assert rep3["attributes"]["str_True"] == True  # noqa: E712
    assert rep3["attributes"]["int_0"] == False  # noqa: E712
    assert rep3["attributes"]["int_1"] == True  # noqa: E712
    assert rep3["attributes"]["float_0"] == False  # noqa: E712
    assert rep3["attributes"]["float_1"] == True  # noqa: E712

    sess.delete(rep["id"])


def test_case_insensitive():
    """It's unclear when flexilims allows to upload case sensitive attributes"""
    # Post will lower case everything:
    sess = flm.Flexilims(
        USERNAME, project_id=PROJECT_ID, password=password, base_url=TEST_URL
    )
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rep = sess.post(
        datatype="session",
        name="test_ran_on_%s" % now,
        attributes=dict(CamelCase="CamelCase", Up="Up", up="up", path="test/session"),
        strict_validation=False,
    )
    assert rep["attributes"]["camelcase"] == "CamelCase"  # noqa: E712
    assert rep["attributes"]["up"] == "up"  # noqa: E712
    assert "Up" not in rep["attributes"]  # noqa: E712
    getitback = sess.get(datatype="session", id=rep["id"])[0]

    assert getitback["attributes"]["camelcase"] == "CamelCase"  # noqa: E712
    assert getitback["attributes"]["up"] == "up"  # noqa: E712
    assert "Up" not in getitback["attributes"]  # noqa: E712

    # Update will not lower case existing attributes:
    attributes = {}
    attributes["Up"] = "Up"
    attributes["up"] = "up"
    attributes["CamelCase"] = "CamelCase"
    attributes["NewAttr"] = "NewAttr"
    rep2 = sess.update_one(
        id=rep["id"], datatype="session", attributes=attributes, strict_validation=False
    )
    assert "CamelCase" in rep2["attributes"]  # noqa: E712
    assert "camelcase" in rep2["attributes"]  # noqa: E712
    assert "up" in rep2["attributes"]  # noqa: E712
    assert "Up" in rep2["attributes"]  # noqa: E712
    assert "NewAttr" in rep2["attributes"]  # noqa: E712


if __name__ == "__main__":
    test_token()
    test_update_token()
    test_session_creation()
    test_safe_execute()
    test_unvalid_request()
    test_get_req()
    test_get_error()
    test_get_children()
    test_get_children_error()
    test_get_project_info()
    test_update_one_errors()
    test_update_one()
    test_update_many_req()
    test_post_req()
    test_post_null()
    test_post_error()
    test_delete()
