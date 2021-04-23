"""Unit tests for the main flexilims wrappers"""

import pytest
import datetime
import flexilims as flm
from flexilims.secret_password import flexilims_passwords

USERNAME = 'blota'
password = flexilims_passwords[USERNAME]
PROJECT_ID = '606df1ac08df4d77c72c9aa4'  # <- test_api project


def test_token():
    tok = flm.get_token(USERNAME, password)
    assert len(tok)


def test_session_creation():
    flm.Flexilims(USERNAME, password)


def test_get_req():
    sess = flm.Flexilims(USERNAME, password)
    sess.get(datatype='session', project_id=PROJECT_ID)
    sess.get(datatype='mouse', project_id=PROJECT_ID)


def test_get_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='InvalidType', project_id=PROJECT_ID)
    assert exc_info.value.args[0] == 'Error 400:  type InvalidType is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='session', project_id='NotAProject')
    assert exc_info.value.args[0] == 'Error 400:  project_id not valid, please provide a hexademical value'


def test_put_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    # get to know how many session there are
    n_sess = len(sess.get(datatype='session'))
    rep = sess.put(datatype='session', update_key='test_attribute',
                   update_value='new_value', query_key=None, query_value=None)
    assert rep == 'updated successfully %d items of type session with test_attribute=new_value' % n_sess
    rep = sess.put(datatype='session', update_key='test_attribute',
                   update_value='new_value', query_key='test_uniq', query_value='nonexistingvalue')
    assert rep == 'updated successfully 0 items of type session with test_attribute=new_value'
    rep = sess.put(datatype='session', query_key='test_uniq', query_value='unique',
                   update_key='test_uniq', update_value='unique')
    assert rep == 'updated successfully 1 items of type session with test_uniq=unique'


def test_post_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    sess.post(datatype='session', name='test_ran_on_%s' % now, attributes=dict())
    sess.post(datatype='recording', name='test_ran_on_%s_with_origin' % now,
              attributes=dict(session='608157fc6943c91ff47e831a', trial=1),
              origin_id='608157fc6943c91ff47e831a', strict_validation=False)


def test_post_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(IOError) as exc:
        sess.post(datatype='recording', name='randomname', project_id=PROJECT_ID,
                  attributes=dict(random_attribute='should fail'))

    with pytest.raises(AssertionError):
        sess.post(datatype='mouse', project_id=None, name='temp', attributes={})
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='NotAType', project_id=PROJECT_ID, name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  type provided is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='mouse', project_id='InvalidProject', name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  project_id not valid, please provide a hexademical value'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID, name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(rec=10), origin_id='605a36c53b38df2abd7757e9',
                  other_relations='605a36be3b38df2abd7757e8')
    err_msg = "Error 400:  allowed fields are [type, name, origin_id, project_id, attributes, custom_entities]"
    assert exc_info.value.args[0] == err_msg
