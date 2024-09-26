"""
Module to run FlexiLIMS in offline mode.

This will use a JSON file as a database instead of the online MongoDB.

Functions to generate the JSON are also included.
"""
import json
import pandas as pd
from copy import deepcopy
from warnings import warn
from flexilims.utils import FlexilimsError, format_results, check_flexilims_validity


class OfflineFlexilims(object):
    def __init__(self, json_file, project_id=None, edit_file=False):
        """Create offline Flexilims session.

        Args:
            json_file: path to the json file
            project_id (optional): hexadecimal id of the project. Not used in offline
                mode, provided for compatibility with the online version.
            edit_file (optional): if True, the file will be editable. Otherwise, only
                the loaded data will be affected. Default to False.

        Returns:
            OfflineFlexilims object
        """
        self.username = "Offline"
        self.base_url = "Offline"
        self._json_file = None
        self._json_data = None
        self._editable = edit_file

        self.session = DummySession()
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
            self._json_data = json.load(f)
        self.log.append(f"Loaded data from {self._json_file}")

    def _format_dataframe(self):
        entities = self._flat_dataframe()
        return pd.DataFrame(format_results(entities))

    def _flat_data(self, keep_children=False):
        """Flatten the json data to a list of dict."""

        def recur_add_children(data, output_list):
            # data keys are the name which are also in valus["name"]. Ignore them.
            for properties in data.values():
                if keep_children:
                    output_list.append(deepcopy(properties))
                else:
                    childless = {k: v for k, v in properties.items() if k != "children"}
                    output_list.append(deepcopy(childless))
                children = properties.get("children", {})
                if children:
                    recur_add_children(children, output_list)
            return output_list

        data_list = []
        recur_add_children(self._json_data, data_list)
        return data_list

    def _find_entity(self, id):
        """Internal function to find a reference to an entity in the database.

        All the other functions should return copies of the entity to avoid modifying
        the "database".

        Args:
            id: hexadecimal id of the entity

        Returns:
            a reference to the entity in the database
        """

        def recur_find(data, id):
            for properties in data.values():
                if properties["id"] == id:
                    return properties
                children = properties.get("children", {})
                if children:
                    found = recur_find(children, id)
                    if found:
                        return found
            return None

        return recur_find(self._json_data, id)

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

        data = pd.DataFrame(self._flat_data())
        filters = dict(
            type=datatype, createdBy=created_by, id=id, name=name, origin_id=origin_id
        )
        for key, value in filters.items():
            if value is not None:
                data = data[data[key] == value]
        if date_created is not None:
            if date_created_operator is None:
                date_created_operator = "gt"

            if date_created_operator == "gt":
                data = data[data["dateCreated"] > date_created]
            elif date_created_operator == "lt":
                data = data[data["dateCreated"] < date_created]
            else:
                raise FlexilimsError("date_created_operator should be 'gt' or 'lt'")
        if query_key is not None:
            valid = []
            for _, el in data.iterrows():
                if query_key in el["attributes"]:
                    if el["attributes"][query_key] == query_value:
                        valid.append(el)
            return valid
        # get returns a list of dict
        return data.to_dict(orient="records")

    def get_children(self, id):
        """Get the children of one entry based on its hexadecimal id

        Args:
            id: hexadecimal id of the object

        Returns:
            a list of dictionary with one element per valid flexilimns entry.
        """
        flat_with_children = self._flat_data(keep_children=True)
        parent = [data for data in flat_with_children if data["id"] == id]
        assert len(parent) == 1, "Parent not found"
        parent = parent[0]
        if "children" not in parent:
            return []
        # remove children below
        output = []
        for child, prop in parent["children"].items():
            childless = {k: v for k, v in prop.items() if k != "children"}
            output.append(deepcopy(childless))
        return output

    def update_token(self):
        """Update the token of the session."""
        print("Offline mode does not need a token")
        return "OFFLINE"

    def get_project_info(self):
        """Get the information of the current project."""
        raise FlexilimsError("Offline mode does not have project info")

    def update_one(
        self,
        id,
        datatype=None,
        origin_id=None,
        name=None,
        attributes=None,
        strict_validation=True,
        allow_nulls=True,
        project_id=None,
    ):
        """Update one entity in the database.

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

        Returns: updated entity
        """

        json_data = {}
        for field in ("name", "origin_id", "attributes"):
            value = locals()[field]
            if value is not None:
                json_data[field] = value

        check_flexilims_validity(json_data)
        entity_to_update = self._find_entity(id)
        if datatype is not None:
            assert entity_to_update["type"] == datatype, "Datatype mismatch"

        if origin_id is not None:
            entity_to_update["origin_id"] = origin_id
            warn(
                "Updating origin_id will break children/parent hierarchy in offline mode"
            )
        if name is not None:
            entity_to_update["name"] = name

        attr2change = {}
        if attributes is not None:
            self._recur_clean(
                json_data["attributes"], attr2change, allow_nulls=allow_nulls
            )
            entity_to_update["attributes"].update(attr2change)

        if self._editable:
            print(f"Updating entity {entity_to_update['name']} in {self._json_file}")
            with open(self._json_file, "w") as f:
                json.dump(self._json_data, f)
        return entity_to_update

    def _recur_clean(self, attr, output, allow_nulls=True, allow_strings=False):
        unvalid = [[], (), None, {}]
        if not allow_strings:
            unvalid.append("")
        for k, v in attr.items():
            if isinstance(v, dict) and len(v):
                output[k] = {}
                self._recur_clean(v, output[k])
                continue
            if isinstance(v, list):
                warn("Updating list might not work in offline mode")

            if v in unvalid:
                if not allow_nulls:
                    continue
                v = None
            output[k] = v
        return output

    def update_many(self, entities):
        raise NotImplementedError("update_many is not implemented in offline mode")

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
        """Create a new entity in the database.

        Args:
            datatype: entity type on flexilims
            name: name of the entity. Must be unique
            attributes: dictionary of attributes for the entity
            project_id: Not used in offline mode
            origin_id: (optional) hexadecimal id of the origin for this entity
            other_relations: (optional) dictionary of other relations for the entity
            strict_validation: Not used in offline mode

        Returns: the created entity
        """
        assert isinstance(attributes, dict)

        # Flexilims cannot handle None value for now
        # requests refuses invalid json, so no NaNs either
        check_flexilims_validity(attributes)
        attr2change = {}
        if attributes is not None:
            self._recur_clean(attributes, attr2change, allow_strings=True)

        json_data = dict(type=datatype, name=name, attributes=attr2change)

        # create a random hexadecimal id
        existing = [el["id"] for el in self._flat_data()]
        n = 0

        def int2hex(n):
            hex_id = hex(n)
            if len(hex_id) < 24:
                hex_id = "0x" + "0" * (24 - len(hex_id)) + hex_id[2:]
            return hex_id

        while int2hex(n) in existing:
            n += 1
        json_data["id"] = int2hex(n)

        if origin_id is not None:
            json_data["origin_id"] = origin_id
        if other_relations is not None:
            json_data["other_relations"] = other_relations
        # Find the parent
        if origin_id is not None:
            parent = self._find_entity(origin_id)
            if "children" not in parent:
                parent["children"] = {}
            parent["children"][name] = json_data
        else:
            self._json_data[name] = json_data
        if self._editable:
            print(f"Adding entity {name} to {self._json_file}")
            with open(self._json_file, "w") as f:
                json.dump(self._json_data, f)
        return json_data


def download_database(flexilims_session, types, verbose=True):
    """Download a FlexiLIMS database as JSON.

    Args:
        flexilims_session (flexilims.Flexilims): Flexilims session, must have project_id
            set.
        types (str or list of str): Entity types to download.
        verbose (bool, optional): Print progress info. Defaults to True.

    Returns:
        dict: JSON data
    """

    if isinstance(types, str):
        types = [types]

    all_data = []
    for datatype in types:
        if verbose:
            print(f"Downloading {datatype}")
        data = flexilims_session.get(datatype=datatype)
        if verbose:
            print(f"    ... {len(data)} {datatype} entities")
        all_data.extend(data)

    if verbose:
        print("Create JSON data")
    # make a dataframe to simplify queries
    df = pd.DataFrame(all_data)
    root_entities = df[df["origin_id"].isna()]
    json_data = {}
    for _, root in root_entities.iterrows():
        json_data[root["name"]] = root.to_dict()
        _add_recursively(json_data[root["name"]], root, df)
    return json_data


def _add_recursively(target, entity, df):
    """Recursively add entities to a dictionary.

    Args:
        target (dict): Target dictionary
        entity (pd.Series): FlexiLIMS entity
        df (pd.DataFrame): DataFrame of entities

    Returns:
        dict: Entity with children added
    """
    assert "children" not in target, "Entity already has a `children` field"
    children = df[df["origin_id"] == entity["id"]]
    if children.empty:
        return target
    target["children"] = {}
    for _, child in children.iterrows():
        target["children"][child["name"]] = child.to_dict()
        _add_recursively(target["children"][child["name"]], child, df)
    return target


def get_token(username, password=None, base_url="OFFLINE"):
    """Get a token from Flexilims API.

    In offline mode, the token is always `OFFLINE` and password is ignored.

    Args:
        username (str): Username for Flexilims
        password (str, optional): Password for Flexilims
        base_url (str, optional): Base URL for Flexilims. Defaults to "OFFLINE".

    Returns:
        str: Token
    """
    return "OFFLINE"


class DummySession(object):
    """Dummy "request" session object for offline mode."""

    def __init__(self) -> None:
        self.headers = {"Authorization": "Bearer OFFLINE"}


if __name__ == "__main__":
    import flexilims as flm
    import flexiznam as flz

    password = flz.config.config_tools.get_password(username="blota", app="flexilims")
    flexilims_session = flm.Flexilims(
        "blota", password=password, project_id="624ae21a73245b6d9992a1f5"
    )

    db = download_database(
        flexilims_session, ["mouse", "session", "recording", "dataset"]
    )
