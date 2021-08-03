"""Unit tests for the main flexilims wrappers"""

import pytest
import datetime
import numpy as np
import flexilims as flm
from flexilims.secret_password import flexilims_passwords

BASE_URL = 'https://flexylims.thecrick.org/flexilims/api/'
USERNAME = 'blota'
password = flexilims_passwords[USERNAME]
PROJECT_ID = '606df1ac08df4d77c72c9aa4'  # <- test_api project


def test_token():
    tok = flm.get_token(USERNAME, password)
    assert len(tok)


def test_session_creation():
    flm.Flexilims(USERNAME, password)


def test_unvalid_request():
    sess = flm.Flexilims(USERNAME, password)
    rep = sess.session.get(sess.base_url + 'get', params=dict(type='recording',
                                                              randomstuff='randomtext',
                                                              project_id=PROJECT_ID))
    assert rep.status_code == 400
    err = flm.main.parse_error(rep.content)
    get_valid_fields = ('[type, name, origin_id, project_id, attributes, '
                        'custom_entities, id, date_created, created_by, '
                        'date_created_operator, query_key, query_value, '
                        'strict_validation, allow_nulls]')
    err_msg = ' randomstuff is not valid. Valid fields are '
    assert err['message'] == err_msg + get_valid_fields


def test_get_req():
    sess = flm.Flexilims(USERNAME, password, base_url=BASE_URL)
    # basic test
    sess.get(datatype='session', project_id=PROJECT_ID)
    r = sess.get(datatype='recording', project_id=PROJECT_ID)
    assert len(r) > 1
    # test all filtering arguments:
    r = sess.get(datatype='recording', project_id=PROJECT_ID, query_key='protocol',
                 query_value='test_prot')
    assert len(r) == 1
    r = sess.get(datatype='dataset', project_id=PROJECT_ID, id='609d2d856d12db1b47d86486')
    assert len(r) == 1
    r = sess.get(datatype='mouse', project_id=PROJECT_ID, id='609d2d856d12db1b47d86486')
    assert len(r) == 0
    r = sess.get(datatype='dataset', project_id=PROJECT_ID, created_by='Petr Znamenskiy')
    assert len(r) > 1
    cutoff = 1620897685816
    r = sess.get(datatype='dataset', project_id=PROJECT_ID, date_created=cutoff,
                 date_created_operator='gt')
    r2 = sess.get(datatype='dataset', project_id=PROJECT_ID, date_created=cutoff)
    assert (len(r) == len(r2)) and all([el in r2 for el in r])
    assert all(el['dateCreated'] >= cutoff for el in r)
    r = sess.get(datatype='dataset', project_id=PROJECT_ID, date_created=cutoff,
                 date_created_operator='lt')
    assert all(el['dateCreated'] <= cutoff for el in r)
    r = sess.get(datatype='dataset', project_id=PROJECT_ID,
                 name='test_ran_on_20210513_144540_dataset')
    assert (len(r) == 1) and (r[0]['name'] == 'test_ran_on_20210513_144540_dataset')


def test_get_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='InvalidType', project_id=PROJECT_ID)
    assert exc_info.value.args[0] == 'Error 400:  type InvalidType is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='session', project_id='NotAProject')
    assert exc_info.value.args[0] == 'Error 400:  project_id not valid, please provide ' \
                                     'a valid hexadecimal value'
    with pytest.raises(OSError) as exc_info:
        sess.get(datatype='session', project_id=PROJECT_ID, id='unvalid')
    assert exc_info.value.args[0] == 'Error 400:  please provide a valid hexadecimal ' \
                                     'value for id'


def test_get_children():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    sess.get_children(id='60803df36943c91ff47e80a8')


def test_get_children_error():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    with pytest.raises(OSError) as exc_info:
        sess.get_children(id='unvalid_id')
    assert exc_info.value.args[0] == 'Error 400:  id not valid, please provide a ' \
                                     'hexadecimal value'


def test_update_one_errors():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    with pytest.raises(OSError) as exc_info:
        sess.update_one(id='609cee832597df357fa25244', datatype='recording')
    assert exc_info.value.args[0] == ('Error 400:  Update failed. &#39;test_uniq&#39; is '
                                      'not defined in lab settings')
    with pytest.raises(OSError) as exc_info:
        sess.update_one(id='609cee832597df357fa25245',
                        name='R101501',
                        datatype='recording',
                        strict_validation=False)
    assert exc_info.value.args[0] == ('Error 400:  Update failed. Check sample name.'
                                      ' Sample R101501 already exist in the project test')
    with pytest.raises(OSError) as exc_info:
        sess.update_one(id='609cee832597df357fa25245',
                        origin_id='randomness',
                        datatype='recording',
                        strict_validation=False)
    assert exc_info.value.args[0] == ('Error 400:  please provide a '
                                      'valid hexadecimal value for origin_id')


def test_update_one():
    # test without project_id
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    entity_id = '609cee832597df357fa25245'
    original = sess.get(datatype='recording', id=entity_id)[0]
    # update nothing
    rep = sess.update_one(id=entity_id, datatype='recording', strict_validation=False)
    assert rep == original
    rep = sess.update_one(id=entity_id, name='R101501_new_name', datatype='recording',
                          strict_validation=False)
    assert rep['name'] == 'R101501_new_name'
    # put back original name
    sess.update_one(id=entity_id, name='R101501', datatype='recording',
                    strict_validation=False)
    orid = original['origin_id']
    other_id = '60803df36943c91ff47e80a8'
    rep = sess.update_one(id=entity_id, origin_id=other_id, datatype='recording',
                          strict_validation=False)
    assert rep['origin_id'] == other_id
    # put back original id
    sess.update_one(id=entity_id, origin_id=orid, datatype='recording',
                    strict_validation=False)
    rep = sess.update_one(id=entity_id, origin_id=other_id, datatype='recording',
                          strict_validation=False,
                          attributes=dict(test_uniq='new_test'))
    assert rep['attributes']['test_uniq'] == 'new_test'
    rep = sess.update_one(id=entity_id,
                          origin_id=other_id,
                          datatype='recording',
                          strict_validation=False,
                          attributes=dict(nested=dict(level='new_test'),
                                          number=12,
                                          nan=np.nan))
    assert isinstance(rep['attributes']['nested'], dict)
    assert rep['attributes']['nested']['level'] == 'new_test'
    assert rep['attributes']['nan'] == 'NaN'
    assert isinstance(rep['attributes']['number'], int)
    # When allow_nulls is False, nothing happens
    rep = sess.update_one(id=entity_id,
                          origin_id=None,
                          datatype='recording',
                          strict_validation=False,
                          allow_nulls=False,
                          attributes=dict(number=21,
                                          nan=''))
    assert rep['attributes']['nan'] == 'NaN'
    assert rep['origin_id'] == other_id
    rep = sess.update_one(id=entity_id,
                          origin_id=other_id,
                          datatype='recording',
                          strict_validation=False,
                          allow_nulls=True,
                          attributes=dict(number='',
                                          nan="",
                                          path='d'))
    # When allow_nulls is True, erase
    assert rep['attributes']['nan'] is None
    assert rep['attributes']['number'] is None


def test_put_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    # get to know how many session there are
    n_sess = len(sess.get(datatype='session'))
    rep = sess.update_many(datatype='session', update_key='test_attribute',
                           update_value='new_value', query_key=None, query_value=None)
    assert rep == ('updated successfully %d items of type session with '
                   'test_attribute=new_value' % n_sess)
    rep = sess.update_many(datatype='session', update_key='test_attribute',
                           update_value='new_value', query_key='test_uniq',
                           query_value='nonexistingvalue')
    assert rep == 'updated successfully 0 items of type session with' \
                  ' test_attribute=new_value'
    rep = sess.update_many(datatype='session',
                           query_key='test_uniq',
                           query_value='unique',
                           update_key='test_uniq',
                           update_value='unique')
    assert rep == 'updated successfully 1 items of type session with test_uniq=unique'
    rep = sess.update_many(datatype='dataset',
                           query_key='path',
                           query_value='unique/fake/path',
                           update_key='is_raw',
                           update_value='yes')
    assert rep == 'updated successfully 0 items of type dataset with is_raw=yes'


def test_post_req():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    rep = sess.post(datatype='session', name='test_ran_on_%s' % now,
                    attributes=dict(path='test/session'))
    rep = sess.post(datatype='recording', name='test_ran_on_%s_with_origin' % now,
                    attributes=dict(session=rep['id'], trial=1,
                                    path='test/session/recording'),
                    origin_id='608157fc6943c91ff47e831a', strict_validation=False)
    sess.post(datatype='dataset', name='test_ran_on_%s_dataset' % now,
              attributes=dict(dataset_type='camera', path='random'),
              origin_id=rep['id'], strict_validation=True)


def test_post_null():
    sess = flm.Flexilims(USERNAME, project_id=PROJECT_ID, password=password)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    sess.post(datatype='session', name='test_ran_on_%s' % now,
              attributes=dict(path='none', empty='', none=None, nan=float('nan'),
                              null='null'),
              strict_validation=False)

def test_post_error():
    sess = flm.Flexilims(USERNAME, password)
    with pytest.raises(IOError):
        sess.post(datatype='recording', name='randomname', project_id=PROJECT_ID,
                  attributes=dict(random_attribute='should fail'))

    with pytest.raises(AssertionError):
        sess.post(datatype='mouse', project_id=None, name='temp', attributes={})
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='NotAType', project_id=PROJECT_ID, name='temp', attributes={})
    assert exc_info.value.args[0] == 'Error 400:  type provided is not defined'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='mouse', project_id='InvalidProject', name='temp',
                  attributes={})
    assert exc_info.value.args[0] == ('Error 400:  please provide a valid hexadecimal '
                                      'value for project_id')
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID,
                  name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(rec=10), origin_id='605a36c53b38df2abd7757e9',
                  other_relations='undefined')
    err_msg = ('Error 400:  other_relations is not valid. Valid fields are [type, name, '
               'origin_id, project_id, attributes, custom_entities, id, date_created, '
               'created_by, date_created_operator, query_key, query_value, '
               'strict_validation, allow_nulls]')
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID,
                  name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(rec=10), origin_id='605a36c53b38df2abd7757e9')
    assert exc_info.value.args[0] == 'Error 400:  origin not found'
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='recording', project_id=PROJECT_ID,
                  name='test_ran_on_%s_with_origin' % 'now',
                  attributes=dict(rec=10), origin_id='608157fc6943c91ff47e831a')
    assert exc_info.value.args[0] == ('Error 400:  &#39;rec&#39; is not defined in lab '
                                      'settings')
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='dataset', project_id=PROJECT_ID, name='suite2p',
                  attributes=dict())
    err_msg = 'Error 400:  &#39;path&#39; is a necessary attribute for dataset'
    assert exc_info.value.args[0] == err_msg
    with pytest.raises(OSError) as exc_info:
        sess.post(datatype='dataset', project_id=PROJECT_ID, name='suite2prandom',
                  attributes=dict(datatype='camOra'))
    err_msg = 'Error 400:  &#39;datatype&#39; is not defined in lab settings'
    assert exc_info.value.args[0] == err_msg
