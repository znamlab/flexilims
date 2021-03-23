"""Unit tests for the main flexilims wrappers"""

import pytest
import datetime
import flexilims.main as flm

username = 'blota'
password = 'blota'
project_id = '605a11a13b38df2abd7756a1'  # <- test_api project


def test_token():
    tok = flm.get_token(username, password)
    assert len(tok)
    tok = flm.get_token(username)
    assert len(tok)


def test_session_createion():
    flm.Flexilims(username)


def test_get_req():
    sess = flm.Flexilims(username)
    sess.get(datatype='session', project_id=project_id)


def test_get_error():
    sess = flm.Flexilims(username)
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='InvalidType', project_id=project_id)
    assert exc_info.value.args[0] == 'Error 400:  type InvalidType is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='session', project_id='NotAProject')
    assert exc_info.value.args[0] == 'Invalid input. Unknown project_id (must be the hexadecimal ID)'


def test_post_req():
    sess = flm.Flexilims(username, project_id=project_id)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    sess.post(datatype='mouse', name='test_ran_on_%s' % now, attributes=dict())


def test_post_error():
    sess = flm.Flexilims(username)
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='mouse', project_id=None, name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  project not found'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='NotAType', project_id=project_id, name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  type provided is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='mouse', project_id='InvalidProject', name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  project id not valid, please provide a hexademical value'
