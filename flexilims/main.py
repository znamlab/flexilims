"""Generic function to interface with flexilims"""

import re
import requests
import warnings
from requests.auth import HTTPBasicAuth
import json

BASE_URL = 'https://flexylims.thecrick.org/flexilims/api/'


class Flexilims(object):

    def __init__(self, username, password, project_id=None, base_url=BASE_URL):
        self.username = username
        self.base_url = base_url
        self.session = None
        self.project_id = project_id
        self.log = []
        self.create_session(password)

    def create_session(self, password):
        """Create a session with authentication information"""
        if self.session is not None:
            print('Session already exists.')
            return

        session = requests.Session()
        tok = get_token(self.username, password)

        session.headers.update(tok)
        self.session = session
        self.log.append('Session created for user %s' % self.username)

    def get(self, datatype, project_id=None, query_key=None, query_value=None, created_by=None,
            id=None, name=None, origin_id=None, date_created=None, date_created_operator=None):
        """Get all the entries of type datatype in the current project

        :param datatype: flexilims type of the object(s)
        :param project_id: hexadecimal id of the project. If None, will use the session default

        Optional argument to filter the results:
        :param id: flexilims id of the object.
        :param name: name of the object
        :param query_key: attribute to filter the results. Filtering is only possible with one attribute
        :param query_value: valid value for attribute name `query_key`
        :param origin_id: hexadecimal id of the origin of the object
        :param created_by: name of the user who created the object
        :param date_created: cutoff date. Only elements with date creation greater (default) or lower than this date
                             will be return (see date_created_operator), in unix time since epoch.
        :param date_created_operator: 'gt' or 'lt' for greater or lower than (default to 'gt') both include exact match

        :return: a list of dictionary with one element per valid flexilimns entry.
        """

        if project_id is None:
            project_id = self.project_id
        params = dict(type=datatype, project_id=project_id)
        if date_created_operator is not None:
            assert(date_created_operator in ('gt', 'lt'))
        elif date_created is not None:
            date_created_operator = 'gt'

        # add all non-None arguments in the list
        args = ('query_key', 'query_value', 'id', 'name', 'origin_id', 'date_created', 'date_created_operator',
                'created_by')
        for arg_name in args:
            if locals()[arg_name] is not None:
                params[arg_name] = locals()[arg_name]

        rep = self.session.get(self.base_url + 'get', params=params)

        if rep.ok and (rep.status_code == 200):
            return self._clean_json(rep)

        self.handle_error(rep)

    def get_children(self, id=None):
        """Get the children of one entry based on its hexadecimal id

        :param id: hexadecimal ID of the parent
        :return: list of dict with one element per child
        """
        rep = self.session.get(self.base_url + 'get-children', params=dict(id=id))
        if rep.ok and (rep.status_code == 200):
            return self._clean_json(rep)

        self.handle_error(rep)

    def put(self, datatype, update_key, update_value, query_key=None, query_value=None, project_id=None,
            strict_validation=False):
        """Update existing object"""
        if project_id is None:
            project_id = self.project_id
        params = dict(type=datatype, project_id=project_id, update_key=update_key, update_value=update_value)
        if query_key is not None:
            params['query_key'] = query_key
        if query_value is not None:
            params['query_value'] = query_value

        address = 'update'
        if strict_validation:
            address += '?strict_validation=true'
            raise NotImplementedError
        rep = self.session.put(self.base_url + address, params=params)
        self.log.append(rep.content)

        if rep.ok and (rep.status_code == 200):
            return rep.content.decode('utf8')
        self.handle_error(rep)

    def post(self, datatype, name, attributes, project_id=None, origin_id=None, other_relations=None,
             strict_validation=True):
        """Create a new entry in the database"""

        if project_id is None:
            project_id = self.project_id
        assert isinstance(project_id, str)
        assert isinstance(attributes, dict)
        json_data = dict(type=datatype, name=name, project_id=project_id,
                         attributes=attributes)
        if origin_id is not None:
            json_data['origin_id'] = origin_id
        if other_relations is not None:
            json_data['other_relations'] = other_relations

        address = 'save'
        if strict_validation:
            address += '?strict_validation=true'
        rep = self.session.post(self.base_url + address, json=json_data)

        if rep.ok and (rep.status_code == 200):
            return self._clean_json(rep)
        self.handle_error(rep)

    def handle_error(self, rep):
        """handles responses that have a status code != 200"""
        # error handling:
        if rep.ok:
            warnings.warn('Warning. Seems ok but I had an unknown status code %s' % rep.status_code)
            warnings.warn('Will return the response object without interpreting it.')
            warnings.warn('see response.json() to (hopefully) get the data.')
            return rep
        if rep.status_code == 400:
            error_dict = parse_error(rep.content)
            raise IOError('Error %d: %s' % (rep.status_code, error_dict['message']))
        if rep.status_code == 404:
            raise IOError('Page not found is the base url: %s?' % (self.base_url + 'get'))
        raise IOError('Unknown error with status code %d' % rep.status_code)

    @staticmethod
    def _clean_json(rep):
        try:
            return rep.json()
        except json.decoder.JSONDecodeError:
            warnings.warn('Temporary fix for dates in json')
            txt = re.sub(r'new Date\((\d*)\)', r'"\1"', rep.content.decode(rep.encoding))
            return json.loads(txt)


def parse_error(error_message):
    """Parse the error message from flexilims bad request

    The messages are html pages with a bold "Type", "Message" and "Description" fields
    """
    if isinstance(error_message, bytes):
        error_message = error_message.decode('utf8')
    m = re.match(pattern='.*<b>Type</b>(.*)</p><p><b>Message</b>(.*)</p><p><b>Description</b>(.*)</p>',
                 string=error_message)
    return {name: v for name, v in zip(('type', 'message', 'description'), m.groups())}


def get_token(username, password):
    """Login to the database and create headers with the proper token
    """
    try:
        rep = requests.post(BASE_URL + 'authenticate', auth=HTTPBasicAuth(username, password))
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError("Cannot connect to flexilims. Are you on the Crick network?")
    if rep.ok:
        token = rep.text
    else:
        raise IOError('Failed to autheticate. Got an error %d' % rep.status_code)

    headers = {"Authorization": "Bearer %s" % token}
    return headers
