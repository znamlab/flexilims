"""Generic function to interface with flexilims"""
import time
import re
import requests
import warnings
from requests.auth import HTTPBasicAuth
from flexilims.utils import (
    FlexilimsError,
    AuthenticationError,
    check_flexilims_validity,
)
import json

BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"


class Flexilims(object):
    """Main class to interface with flexilims

    Args:
        username: username to connect to flexilims
        password: password to connect to flexilims
        project_id: hexadecimal id of the project to use
        base_url: base url of the flexilims server
        token: if you already have a token, you can pass it here
    """

    def __init__(
        self, username, password, project_id=None, base_url=BASE_URL, token=None
    ):
        assert isinstance(base_url, str), "base_url must be a string"
        assert base_url.endswith("api/"), "base_url must end with 'api/'"

        self.username = username
        self.password = password
        self.base_url = base_url
        self.session = None
        self.project_id = project_id
        self.log = []
        self.create_session(password, token=token)

    def create_session(self, password, token=None):
        """Create a session with authentication information"""
        if self.session is not None:
            print("Session already exists.")
            return

        session = requests.Session()
        if token is None:
            token = get_token(self.username, password, self.base_url)

        session.headers.update(token)
        self.session = session
        self.log.append("Session created for user %s" % self.username)

    def update_token(self, timeout=600):
        """Update the token in the session"""
        token = None
        elapsed_time = 0
        while token is None and elapsed_time < timeout:
            elapsed_time += 5
            try:
                token = get_token(self.username, self.password, self.base_url)
            except IOError:
                print("Failed to get a token. Retrying in 5 seconds.")
                time.sleep(5)
        if token is None:
            raise IOError("Failed to get a token. Timeout reached.")
        self.session.headers.update(token)

    def get(
        self,
        datatype=None,
        project_id=None,
        query_key=None,
        query_value=None,
        created_by=None,
        id=None,
        name=None,
        origin_id=None,
        date_created=None,
        date_created_operator=None,
    ):
        """Get all the entries of type datatype in the current project

        Args:
            datatype: flexilims type of the object(s)
            project_id: hexadecimal id of the project. If None, will use the session
                        default
            id: flexilims id of the object.
            name: name of the object
            query_key: attribute to filter the results. Filtering is only possible with
                       one attribute
            query_value: valid value for attribute name `query_key`
            origin_id: hexadecimal id of the origin of the object
            created_by: name of the user who created the object
            date_created: cutoff date. Only elements with date creation greater (default)
                         or lower than this date will be return (see
                         date_created_operator), in unix time since epoch.
            date_created_operator: 'gt' or 'lt' for greater or lower than (default to
                                   'gt') both include exact match

        Returns:
            a list of dictionary with one element per valid flexilimns entry.
        """

        if project_id is None:
            project_id = self.project_id
        params = dict(type=datatype, project_id=project_id)
        if date_created_operator is not None:
            assert date_created_operator in ("gt", "lt")
        elif date_created is not None:
            date_created_operator = "gt"

        # add all non-None arguments in the list
        args = (
            "query_key",
            "query_value",
            "id",
            "name",
            "origin_id",
            "date_created",
            "date_created_operator",
            "created_by",
        )
        for arg_name in args:
            if locals()[arg_name] is not None:
                params[arg_name] = locals()[arg_name]

        return self.safe_execute(
            "json", self.session.get, self.base_url + "get", params=params
        )

    def get_children(self, id):
        """Get the children of one entry based on its hexadecimal id

        Args:
            id: hexadecimal id of the parent object
        """
        return self.safe_execute(
            "json", self.session.get, self.base_url + "get-children", params=dict(id=id)
        )

    def get_project_info(self):
        """Get the list of existing project and their properties

        Returns:
            proj_list (list of dict): a list with one dictionary per project
        """
        return self.safe_execute("json", self.session.get, self.base_url + "projects")

    def update_one(
        self,
        id,
        datatype,
        origin_id=None,
        name=None,
        attributes=None,
        strict_validation=True,
        allow_nulls=True,
        project_id=None,
    ):
        """Update one existing entity

        Args:
            id: hexadecimal id of the entity to update on flexilims
            datatype: entity type on flexilims, used to find the entity to update
            origin_id: (optional) new hexadecimal id of the origin for this entity
            name: (optional) new name for this entity. Must be unique
            attributes: (optional) dictionary of attributes to update the entity
            strict_validation: (True by default) if True, check that all attributes are
                               defined in the lab settings
            allow_nulls: (True by default) if True, an attribute set to "" or '' will be
                         set to null, if False, such values will be ignored and
                         not updated.
                         Note that required attributes cannot be set to None.
            project_id: hexadecimal project id. Use self.project if None.

        Returns: reply from flexilims
        """
        if project_id is None:
            project_id = self.project_id

        params = dict(type=datatype, id=id)
        json_data = {}
        for field in ("name", "origin_id", "attributes"):
            value = locals()[field]
            if value is not None:
                json_data[field] = value

        check_flexilims_validity(json_data)

        address = "update-one"
        # add flags
        if strict_validation:
            params["strict_validation"] = "true"
        if allow_nulls:
            params["allow_nulls"] = "true"
        return self.safe_execute(
            "json",
            self.session.put,
            self.base_url + address,
            params=params,
            json=json_data,
        )

    def update_many(
        self,
        datatype,
        update_key,
        update_value,
        query_key=None,
        query_value=None,
        project_id=None,
        strict_validation=False,
    ):
        """Update many existing entity

        Args:
            datatype: entity type on flexilims, used to find the entity to update
            update_key: attribute that you want to update
            update_value: new value for the attributes
            query_key (optional): attribute to select which entries to update
            query_value (optional): valid value for query_key
            project_id (optional): hexadecimal project id. Use self.project if None.
            strict_validation (True by default) if True, check that all attributes are
                               defined in the lab settings

        Returns: reply from flexilims
        """

        if project_id is None:
            project_id = self.project_id
        for n, w in zip(["update_key", "query_key"], [update_key, query_key]):
            if (w is not None) and (w.lower() != w):
                warnings.warn("`%s` should probably be lower case. Trying anyways" % n)
        params = dict(
            type=datatype,
            project_id=project_id,
            update_key=update_key,
            update_value=update_value,
        )
        if query_key is not None:
            params["query_key"] = query_key
        if query_value is not None:
            params["query_value"] = query_value

        check_flexilims_validity(params)

        address = "update-many"
        if strict_validation:
            address += "?strict_validation=true"

        return self.safe_execute(
            "content", self.session.put, self.base_url + address, params=params
        )

    def post(
        self,
        datatype,
        name,
        attributes,
        project_id=None,
        origin_id=None,
        other_relations=None,
        strict_validation=True,
    ):
        """Create a new entry in the database

        Args:
            datatype: entity type on flexilims
            name: new name for this entity. Must be unique
            attributes: dictionary of attributes to update the entity. Any
                        mangodb-compatible element (including nested dictionary) is
                        supported
            project_id: hexadecimal project id. Use self.project if None.
            origin_id: (optional) hexadecimal id of the origin for this entity
            other_relations (optional): not used. Ask Mike Gavrielides to know more
            strict_validation: (True by default) if True, check that all attributes are
                               defined in the lab settings

        Returns: reply from flexilims
        """

        if project_id is None:
            project_id = self.project_id
        assert isinstance(project_id, str)
        assert isinstance(attributes, dict)

        # Flexilims cannot handle None value for now
        # requests refuses invalid json, so no NaNs either
        check_flexilims_validity(attributes)

        json_data = dict(
            type=datatype, name=name, project_id=project_id, attributes=attributes
        )
        if origin_id is not None:
            json_data["origin_id"] = origin_id
        if other_relations is not None:
            json_data["other_relations"] = other_relations

        address = "save"
        if strict_validation:
            address += "?strict_validation=true"

        return self.safe_execute(
            "json", self.session.post, self.base_url + address, json=json_data
        )

    def safe_execute(self, mode, function, *args, **kwargs):
        """Execute a function and update the token if needed

        Args:
            mode: 'json' or 'content' to return the json or the content of the response
            function: function to execute
            *args: arguments to pass to the function
            **kwargs: keyword arguments to pass to the function

        Returns:
            json or content of the response
        """
        try:
            rep = function(*args, **kwargs)
            self.handle_error(rep)
        except AuthenticationError as e:
            # try to update the token and retry
            self.update_token()
            rep = function(*args, **kwargs)
            self.handle_error(rep)
        if mode == "json":
            return rep.json()
        elif mode == "content":
            return rep.content.decode("utf8")
        else:
            raise ValueError("mode must be 'json' or 'content'")

    def delete(self, id):
        """Delete an entity

        Args:
            id: hexadecimal id of the entity to delete
        """
        return self.safe_execute(
            "content", self.session.delete, self.base_url + "delete", params=dict(id=id)
        )

    def handle_error(self, rep):
        """handles responses that have a status code != 200"""
        if rep.status_code == 200:
            return
        # error handling:
        if rep.ok:
            warnings.warn(
                "Warning. Seems ok but I had an unknown status code %s"
                % rep.status_code
            )
            warnings.warn("Will return the response object without interpreting it.")
            warnings.warn("see response.json() to (hopefully) get the data.")
            return rep
        if rep.status_code == 400:
            error_dict = parse_error(rep.content)
            raise IOError("Error %d: %s" % (rep.status_code, error_dict["message"]))
        if rep.status_code == 404:
            raise IOError(
                "Page not found is the base url: %s?" % (self.base_url + "get")
            )
        if rep.status_code == 403:
            raise AuthenticationError("Forbidden. Are you logged in?")
        raise IOError("Unknown error with status code %d" % rep.status_code)

    @property
    def project_id(self):
        return self._project_id

    @project_id.setter
    def project_id(self, value):
        if value is not None:
            value = str(value)
            try:
                int(value, 16)
            except ValueError:
                raise FlexilimsError(
                    "project_id must be a hexadecimal project id. Got %s" % value
                )
            if len(value) != 24:
                raise FlexilimsError(
                    "project_id must be a 24 characters long project id."
                    " Got %s" % value
                )
        self._project_id = value


def parse_error(error_message):
    """Parse the error message from flexilims bad request

    The messages are html pages with a bold "Type", "Message" and "Description" fields
    """
    if isinstance(error_message, bytes):
        error_message = error_message.decode("utf8")
    regexp = (
        ".*<b>Type</b>(.*)</p><p><b>Message</b>(.*)</p><p><b>Description</b>(.*)</p>"
    )
    m = re.match(pattern=regexp, string=error_message)
    return {name: v for name, v in zip(("type", "message", "description"), m.groups())}


def get_token(username, password, base_url=BASE_URL):
    """Login to the database and create headers with the proper token"""
    try:
        rep = requests.post(
            base_url + "authenticate", auth=HTTPBasicAuth(username, password)
        )
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError(
            "Cannot connect to flexilims. " "Are you on the Crick network?"
        )
    if rep.ok:
        token = rep.text
    else:
        raise IOError("Failed to authenticate. Got an error %d" % rep.status_code)

    headers = {"Authorization": "Bearer %s" % token}
    return headers
