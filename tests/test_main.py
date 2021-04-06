"""Unit tests for the main flexilims wrappers"""

import pytest
import datetime
import flexilims as flm
from resources.secret_password import flexilims_passwords

username = 'blota'
password = flexilims_passwords['blota']
project_id = '605a11a13b38df2abd7756a1'  # <- test_api project


def test_token():
    tok = flm.get_token(username, password)
    assert len(tok)
    tok = flm.get_token(username)
    assert len(tok)


def test_session_creation():
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


def test_put_req():
    sess = flm.Flexilims(username, project_id=project_id)
    # get to know how many session there are
    n_sess = len(sess.get(datatype='session'))
    rep = sess.put(datatype='session', update_key='test_attribute',
                   update_value='new_value', query_key=None, query_value=None)
    assert rep == 'updated successfully %d items of type session with test_attribute=new_value'%n_sess
    rep = sess.put(datatype='session', update_key='test_attribute',
                   update_value='new_value', query_key='test_uniq', query_value='nonexistingvalue')
    assert rep == 'updated successfully 0 items of type session with test_attribute=new_value'
    rep = sess.put(datatype='session', query_key='test_uniq', query_value='unique',
                   update_key='test_uniq', update_value='unique')
    assert rep == 'updated successfully 1 items of type session with test_uniq=unique'


def test_post_req():
    sess = flm.Flexilims(username, project_id=project_id)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    sess.post(datatype='session', name='test_ran_on_%s' % now, attributes=dict())
    sess.post(datatype='recording', name='test_ran_on_%s_with_origin' % now,
              attributes=dict(session='605a36c53b38df2abd7757e9', trial=1),
              origin_id='605a36c53b38df2abd7757e9')

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
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=project_id, name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(), origin_id='605a36c53b38df2abd7757e9', other_relations='605a36be3b38df2abd7757e8')
    assert exc_info.value.args[0] == 'Unhandled error. Contact Computing STP'
