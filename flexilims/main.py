"""Generic function to interface with flexilims"""

import re
import requests
import warnings
from requests.auth import HTTPBasicAuth

BASE_URL = 'https://flexylims.thecrick.org/flexilims/api/'


class Flexilims(object):

    def __init__(self, username, project_id=None, base_url=BASE_URL):
        self.username = username
        self.base_url = base_url
        self.session = None
        self.project_id = project_id
        self.log = []
        self.create_session()

    def create_session(self):
        """Create a session with authentification information"""
        if self.session is not None:
            print('Session already exists.')
            return

        session = requests.Session()
        tok = get_token(self.username)

        session.headers.update(tok)
        self.session = session
        self.log.append('Session created for user %s' % self.username)

    def get(self, datatype, project_id=None):

        if project_id is None:
            project_id = self.project_id

        rep = self.session.get(self.base_url + 'get', params=dict(type=datatype, project_id=project_id))
        self.log.append(rep.content)

        if rep.ok and (rep.status_code == 200):
            return rep.json()
        elif rep.ok:
            warnings.warn('Warning. Seems ok but I had an unknown status code %s' % rep.status_code)
            warnings.warn('Will return the response object')
            return rep
        if rep.status_code == 400:
            error_dict = parse_error(rep.content)
            raise IOError('Error %d: %s' % (rep.status_code, error_dict['message']))

        if rep.status_code == 500:
            if "invalid hexadecimal representation of an ObjectId:" in rep.content.decode('utf8'):
                raise IOError('Invalid input. Unknown project_id (must be the hexadecimal ID)')

    def put(self, datatype, update_key, update_value, query_key=None, query_value=None, project_id=None):
        """Update existing object"""
        if project_id is None:
            project_id = self.project_id
        params = dict(type=datatype, project_id=project_id, updateKey=update_key, updateValue=update_value)
        if query_key is not None:
            params['queryKey'] = query_key
        if query_value is not None:
            params['queryValue'] = query_value

        rep = self.session.put(self.base_url + 'update', params=params)
        self.log.append(rep.content)

        if rep.ok and (rep.status_code == 200):
            return rep.content.decode('utf8')
        elif rep.ok:
            warnings.warn('Warning. Seems ok but I had an unknown status code %s' % rep.status_code)
            warnings.warn('Will return the response object')
            return rep
        error_dict = parse_error(rep.content)
        raise IOError('Error %d: %s' % (rep.status_code, error_dict['message']))

    def post(self, datatype, name, attributes, project_id=None, origin_id=None, other_relations=None):
        """Create a new entry in the database"""

        if project_id is None:
            project_id = self.project_id

        assert isinstance(attributes, dict)
        json = dict(type=datatype, name=name, project_id=project_id,
                    attributes=attributes)
        if origin_id is not None:
            json['origin_id'] = origin_id
        if other_relations is not None:
            json['other_relations'] = other_relations

        rep = self.session.post(self.base_url + 'save', json=json)

        if rep.ok and (rep.status_code == 200):
            return rep.json()
        elif rep.ok:
            warnings.warn('Warning. Seems ok but I had an unknown status code %s' % rep.status_code)
            warnings.warn('Will return the response object')
            return rep
        if rep.status_code == 500:
            raise IOError('Unhandled error. Contact Computing STP')
        error_dict = parse_error(rep.content)
        raise IOError('Error %d: %s' % (rep.status_code, error_dict['message']))


def parse_error(error_message):
    """Parse the error message from flexilims bad request
    
    The messages are html pages with a bold "Type", "Message" and "Description" fields
    """
    if isinstance(error_message, bytes):
        error_message = error_message.decode('utf8')
    m = re.match(pattern='.*<b>Type</b>(.*)</p><p><b>Message</b>(.*)</p><p><b>Description</b>(.*)</p>',
                 string=error_message)
    return {name: v for name, v in zip(('type', 'message', 'description'), m.groups())}


def get_token(username, password=None):
    """Login to the database and create headers with the proper token

    If the password is not provided, we will attempt to read it from the
    password_dict found in secret_password.py
    """

    if password is None:
        try:
            from resources import secret_password
        except ImportError:
            print('Cannot load flexilims.secret_password')
            return
        password = secret_password.flexilims_passwords[username]

    rep = requests.post(BASE_URL + 'authenticate', auth=HTTPBasicAuth(username, password))
    if rep.ok:
        token = rep.text
    else:
        rep.raise_for_status()

    headers = {"Authorization": "Bearer %s" % token}
    return headers


if __name__ == '__main__':
    sess = Flexilims('blota')
    sess.project_id = '605a11a13b38df2abd7756a1'
    rep = sess.get(datatype='session')
    print('Done')
