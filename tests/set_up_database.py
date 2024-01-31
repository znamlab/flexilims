"""
There is no API to delete stuff.

To clean the database from time to time I have to delete everything and reset the test
data. I usually keep one mouse: `test_mouse`, id 6094f7212597df357fa24a8c

This file just does that.
"""
import flexilims as flm
from flexiznam.config.config_tools import get_password

USERNAME = "blota"
password = get_password(username=USERNAME, app="flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"
flm_sess = flm.Flexilims(USERNAME, password)

flm_sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
sess_rep = flm_sess.post(
    datatype="session",
    name="test_session",
    origin_id=MOUSE_ID,
    attributes=dict(path="test/session", test_uniq="unique"),
    strict_validation=False,
)
rec_rep = flm_sess.post(
    datatype="recording",
    name="test_recording",
    origin_id=sess_rep["id"],
    attributes=dict(rec_attr="attribute of recording", path="test/session/recording"),
    strict_validation=False,
)
ds_rep = flm_sess.post(
    datatype="dataset",
    name="test_dataset",
    origin_id=rec_rep["id"],
    attributes=dict(
        ds_attr="attribute of recording",
        path="test/session/recording",
        dataset_type="test_dataset",
    ),
    strict_validation=False,
)
