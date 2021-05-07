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
    r = sess.get(datatype='recording', project_id=PROJECT_ID)
    assert len(r) > 1
    r2 = sess.get(datatype='recording', project_id=PROJECT_ID, query_key='protocol',
                  query_value='test_prot')
    assert len(r2) == 1


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
    rep = sess.put(datatype='dataset', query_key='path', query_value='unique/fake/path',
                   update_key='is_raw', update_value='yes')
    assert rep == 'updated successfully 1 items of type dataset with is_raw=yes'

def test_update_by_id():
    rep = sess.put(datatype='recording', query_key='id', query_value='6093e0fa2597df357fa24887',
                   update_key='test_update_by_id', update_value='updated_id_6093e0f...')
    assert rep == 'updated successfully 1 items of type recording with test_update_by_id=updated_id_6093e0f...'


def test_post_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    rep = sess.post(datatype='session', name='test_ran_on_%s' % now, attributes=dict())
    rep = sess.post(datatype='recording', name='test_ran_on_%s_with_origin' % now,
              attributes=dict(session=rep['id'], trial=1),
              origin_id='608157fc6943c91ff47e831a', strict_validation=False)
    rep = sess.post(datatype='dataset', name='test_ran_on_%s_dataset' % now,
              attributes=dict(datatype='camera', path='random'),
              origin_id=rep['id'], strict_validation=True)


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
                  other_relations='undefined')
    err_msg = "Error 400:  allowed fields are [type, name, origin_id, project_id, attributes, custom_entities]"
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID, name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(rec=10), origin_id='605a36c53b38df2abd7757e9')
    assert exc_info.value.args[0] == 'Error 400:  origin not found'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID, name='test_ran_on_%s_with_origin' % 'now',
                      attributes=dict(rec=10), origin_id='609407f92597df357fa2489d')
    assert exc_info.value.args[0] == 'Error 400:  &#39;rec&#39; is not defined in lab settings'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='dataset', project_id=PROJECT_ID, name='suite2p', attributes=dict())
    err_msg = 'Error 400:  &#39;datatype&#39; is a necessary attribute for dataset'
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='dataset', project_id=PROJECT_ID, name='suite2prandom', attributes=dict(datatype='camOra'))
    err_msg = 'Error 400:  &#39;camOra&#39; is not a valid value for datatype'
    assert exc_info.value.args[0] == err_msg
