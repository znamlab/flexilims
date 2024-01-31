"""
Module to run FlexiLIMS in offline mode.

This will use a JSON file as a database instead of the online MongoDB.

Functions to generate the JSON are also included.
"""
import yaml
import pandas as pd
from flexilims.utils import FlexilimsError, format_results


class OffFlexilims(object):
    def __init__(self, json_file, project_id=None):
        """Create offline Flexilims session."""
        self.username = "Offline"
        self.base_url = "Offline"
        self._json_file = None
        self._json_data = None
        self._dataframe = None

        self.session = None
        self.project_id = project_id
        self.log = []
        self.json_file = json_file

    @property
    def json_file(self):
        """Path to JSON file."""
        return self._json_file

    @json_file.setter
    def json_file(self, value):
        self._json_file = value
        with open(self._json_file) as f:
            self._json_data = yaml.load(f, Loader=yaml.SafeLoader)
        self._format_dataframe()
        self.log.append(f"Loaded data from {self._json_file}")

    def _format_dataframe(self):
        entities = []

        def add_entity(entities, parent):
            for child in parent["children"].values():

                entities.append(child)
                add_entity(entities, child)
            return entities

        for root_name, entity in self._json_data.items():
            entities.append(entity)
            add_entity(entities, entity)
        self._dataframe = format_results(entities)

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
        if project_id is not None:
            print("Offline mode ignores project_id")
        raise NotImplementedError()

    def get_children(self, id=None):
        """Get the children of one entry based on its hexadecimal id

        :param id: hexadecimal ID of the parent
        :return: list of dict with one element per child
        """
        raise NotImplementedError()


def download_database(flexilims_session, root_datatypes=("mouse"), verbose=True):
    """Download a FlexiLIMS database as JSON.

    Args:
        username (str): Username for FlexiLIMS
        password (str): Password for FlexiLIMS
        project_id (str): Hexadecimal ID of the project
        root_datatypes (tuple, optional): Tuple of datatypes that can be root (i.e.
            have no `origin_id`). Defaults to ("mouse").
        verbose (bool, optional): Print progress info. Defaults to True.

    Returns:
        dict: JSON data
    """

    if isinstance(root_datatypes, str):
        root_datatypes = [root_datatypes]

    if verbose:
        print("Downloading root entities")
    root_entities = []
    for datatype in root_datatypes:
        candidates = flexilims_session.get(datatype=datatype)
        for c in candidates:
            if "origin_id" in c:
                if not verbose:
                    continue
                print(f"{c['name']} is a `{datatype}` but not root (has `origin_id`)")
            else:
                root_entities.append(c)

    if verbose:
        print(f"Downloading children for {len(root_entities)} entity/ies")
    json_data = {}
    for i_root, entity in enumerate(root_entities):
        json_data[entity["name"]] = download_children(entity, flexilims_session)
        if verbose:
            print(f"    ... {i_root + 1} of {len(root_entities)} entity/ies")
    return json_data


def download_children(entity, flexilims_session):
    """Recursively download children of an entity.

    Args:
        entity (dict): FlexiLIMS entity
        flm_sess (flexilims.Flexilims): Flexilims session, must have project_id set

    Returns:
        dict: Entity with children added
    """
    assert "children" not in entity, "Entity already has a `children` field"
    entity["children"] = {}
    for child in flexilims_session.get_children(entity["id"]):
        entity["children"][child["name"]] = download_children(child, flexilims_session)
    return entity
