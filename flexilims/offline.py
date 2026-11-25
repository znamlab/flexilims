"""
Module to run FlexiLIMS in offline mode.

This will use a JSON file as a database instead of the online MongoDB.

Functions to generate the JSON are also included.
"""

import json
import logging
import math
from collections import defaultdict
from copy import deepcopy
from warnings import warn

import pandas as pd

from flexilims.utils import FlexilimsError, check_flexilims_validity, format_results

logger = logging.getLogger(__name__)


def _is_missing_origin(value):
    """Return True if an `origin_id` value represents no parent (None or NaN)."""
    return value is None or (isinstance(value, float) and math.isnan(value))


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
        self._json_file = json_file
        self._json_data = {}
        self._editable = edit_file
        self._flat_cache = None
        self._flat_cache_with_children = None
        self._entity_index = None

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
        self._invalidate_cache()
        self.log.append(f"Loaded data from {self._json_file}")

    def _invalidate_cache(self):
        """Invalidate the cached flattened views of `_json_data`."""
        self._flat_cache = None
        self._flat_cache_with_children = None
        self._entity_index = None

    def _format_dataframe(self):
        entities = self._flat_data()
        return pd.DataFrame(format_results(entities))

    def _flat_data(self, keep_children=False):
        """Flatten the json data to a list of dict.

        The result is cached (per `keep_children` value) and reused until the
        underlying `_json_data` is mutated, since building it involves a full
        recursive walk plus a `deepcopy` of every entity.
        """
        cache_attr = "_flat_cache_with_children" if keep_children else "_flat_cache"
        cached = getattr(self, cache_attr)
        if cached is not None:
            return cached

        def recur_add_children(data, output_list):
            # data keys are the name which are also in values["name"]. Ignore them.
            for properties in data.values():
                if keep_children:
                    entry = deepcopy(properties)
                else:
                    childless = {k: v for k, v in properties.items() if k != "children"}
                    entry = deepcopy(childless)
                if "origin_id" in entry and _is_missing_origin(entry["origin_id"]):
                    entry["origin_id"] = None
                output_list.append(entry)
                children = properties.get("children", {})
                if children:
                    recur_add_children(children, output_list)
            return output_list

        data_list = []
        recur_add_children(self._json_data, data_list)
        setattr(self, cache_attr, data_list)
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
        if self._entity_index is None:
            index = {}

            def recur_index(data):
                for properties in data.values():
                    index[properties["id"]] = properties
                    children = properties.get("children", {})
                    if children:
                        recur_index(children)

            recur_index(self._json_data)
            self._entity_index = index

        return self._entity_index.get(id)

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
        cross_project_entity=False,
        limit=None,
    ):
        """Get all the entries of type datatype in the current project

        Args:
            datatype: flexilims type of the object(s)
            project_id: hexadecimal id of the project. If None, will use the session
                default
            id: flexilims id of the object.
            name: name of the object
            query_key: attribute name (or sequence of attribute names) to filter the
                results. Multiple attributes are combined with AND.
            query_value: valid value (or sequence of values, in the same order as
                `query_key`) for `query_key`.
            origin_id: hexadecimal id of the origin of the object
            created_by: name of the user who created the object
            date_created: cutoff date. Only elements with date creation greater
                (default) or lower than this date will be return (see
                date_created_operator), in unix time since epoch.
            date_created_operator: 'gt' or 'lt' for greater or lower than (default to
                'gt') both include exact match
            cross_project_entity (bool): whether to include cross project entity in the
                results (default to False). When True, project filtering is skipped.
            limit (int): maximum number of results to return (default to None)

        Returns:
            a list of dictionary with one element per valid flexilimns entry.
        """

        if project_id is None:
            project_id = self.project_id

        if date_created is not None:
            if date_created_operator is None:
                date_created_operator = "gt"
            if date_created_operator not in ("gt", "lt"):
                raise FlexilimsError("date_created_operator should be 'gt' or 'lt'")

        query_pairs = None
        if query_key is not None:
            if isinstance(query_key, (list, tuple)):
                if not isinstance(query_value, (list, tuple)) or len(query_key) != len(
                    query_value
                ):
                    raise FlexilimsError(
                        "`query_value` must be a sequence with the same length as "
                        "`query_key`"
                    )
                query_pairs = list(zip(query_key, query_value))
            else:
                query_pairs = [(query_key, query_value)]

        filters = dict(
            type=datatype,
            createdBy=created_by,
            id=id,
            name=name,
            origin_id=origin_id,
            project=None if cross_project_entity else project_id,
        )
        active_filters = {k: v for k, v in filters.items() if v is not None}

        results = []
        for el in self._flat_data():
            if any(el.get(k) != v for k, v in active_filters.items()):
                continue
            if date_created is not None:
                el_date = el.get("dateCreated")
                if el_date is None:
                    continue
                if date_created_operator == "gt" and not (el_date >= date_created):
                    continue
                if date_created_operator == "lt" and not (el_date <= date_created):
                    continue
            if query_pairs is not None:
                attrs = el.get("attributes", {})
                if not all(k in attrs and attrs[k] == v for k, v in query_pairs):
                    continue
            results.append(deepcopy(el))
            if limit is not None and len(results) >= limit:
                break
        return results[:limit] if limit is not None else results

    def get_children(self, id):
        """Get the children of one entry based on its hexadecimal id

        Args:
            id: hexadecimal id of the object

        Returns:
            a list of dictionary with one element per valid flexilimns entry.
        """
        parent = self._find_entity(id)
        if parent is None:
            raise FlexilimsError(f"Entity with id '{id}' not found")
        if "children" not in parent:
            return []
        # remove children below
        output = []
        for prop in parent["children"].values():
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
            project_id: deprecated and ignored (`PUT /update-one` does not accept
                `project_id`).

        Returns: updated entity
        """
        if project_id is not None:
            warn(
                "`project_id` is deprecated in `update_one` and ignored.",
                DeprecationWarning,
                stacklevel=2,
            )

        cleaned_attributes = None
        if attributes is not None:
            cleaned_attributes = check_flexilims_validity(attributes)

        entity_to_update = self._find_entity(id)
        if entity_to_update is None:
            raise FlexilimsError(f"Entity with id '{id}' not found")
        if datatype is not None:
            assert entity_to_update["type"] == datatype, "Datatype mismatch"

        if origin_id is not None:
            entity_to_update["origin_id"] = origin_id
            warn("Updating origin_id will break children/parent hierarchy")
        if name is not None and name != entity_to_update["name"]:
            entity_project = entity_to_update.get("project")
            for existing_el in self._flat_data():
                if existing_el["id"] == id:
                    continue
                if existing_el["name"] == name and (
                    entity_project is None
                    or existing_el.get("project") == entity_project
                ):
                    raise FlexilimsError(f"Entity with name '{name}' already exists")
            container, old_key = self._find_entity_container(id)
            if container is not None and name in container:
                raise FlexilimsError(f"Entity with name '{name}' already exists")
            if container is not None and old_key is not None:
                container[name] = container.pop(old_key)
            entity_to_update["name"] = name

        attr2change = {}
        if cleaned_attributes is not None:
            self._recur_clean(cleaned_attributes, attr2change, allow_nulls=allow_nulls)
            entity_to_update.setdefault("attributes", {}).update(attr2change)

        if self._editable:
            print(f"Updating entity {entity_to_update['name']} in {self._json_file}")
            with open(self._json_file, "w") as f:
                json.dump(self._json_data, f)
        self._flat_cache = None
        self._flat_cache_with_children = None
        return deepcopy(entity_to_update)

    def _find_entity_container(self, entity_id):
        """Return `(container_dict, key)` holding the entity with `entity_id`."""

        def recur_search(container):
            for key, properties in container.items():
                if properties["id"] == entity_id:
                    return container, key
                children = properties.get("children", {})
                if children:
                    found = recur_search(children)
                    if found[0] is not None:
                        return found
            return None, None

        return recur_search(self._json_data)

    def _recur_clean(self, attr, output, allow_nulls=True, allow_strings=False):
        invalid = [[], (), None, {}]
        if not allow_strings:
            invalid.append("")
        for k, v in attr.items():
            if isinstance(v, dict) and len(v):
                output[k] = {}
                self._recur_clean(
                    v, output[k], allow_nulls=allow_nulls, allow_strings=allow_strings
                )
                continue
            if isinstance(v, list):
                warn("Updating list might not work in offline mode")

            if v in invalid:
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
        strict_validation=True,
    ):
        """Create a new entity in the database.

        Args:
            datatype: entity type on flexilims
            name: name of the entity. Must be unique
            attributes: dictionary of attributes for the entity
            project_id: Not used in offline mode
            origin_id: (optional) hexadecimal id of the origin for this entity
            strict_validation: Not used in offline mode

        Returns: the created entity
        """
        assert isinstance(attributes, dict)

        # Flexilims cannot handle None value for now
        # requests refuses invalid json, so no NaNs either
        attributes = check_flexilims_validity(attributes)
        attr2change = {}
        if attributes is not None:
            self._recur_clean(attributes, attr2change, allow_strings=True)

        if project_id is None:
            project_id = self.project_id

        # Enforce name uniqueness before mutating the database
        for existing_el in self._flat_data():
            if existing_el["name"] == name and (
                project_id is None or existing_el.get("project") == project_id
            ):
                raise FlexilimsError(f"Entity with name '{name}' already exists")

        # Validate parent before allocating an id or mutating state
        parent = None
        if origin_id is not None:
            parent = self._find_entity(origin_id)
            if parent is None:
                raise FlexilimsError(f"Origin entity with id '{origin_id}' not found")
            if name in parent.get("children", {}):
                raise FlexilimsError(f"Entity with name '{name}' already exists")
        elif name in self._json_data:
            raise FlexilimsError(f"Entity with name '{name}' already exists")

        json_data = dict(type=datatype, name=name, attributes=attr2change)
        if project_id is not None:
            json_data["project"] = project_id

        # create a random hexadecimal id
        existing = {el["id"] for el in self._flat_data()}
        n = 0

        def int2hex(n):
            hex_id = hex(n)
            if len(hex_id) < 24:
                hex_id = "0x" + "0" * (24 - len(hex_id)) + hex_id[2:]
            return hex_id

        while int2hex(n) in existing:
            n += 1
        json_data["id"] = int2hex(n)

        json_data["origin_id"] = origin_id
        if origin_id is not None:
            assert parent is not None
            if "children" not in parent:
                parent["children"] = {}
            parent["children"][name] = json_data
        else:
            self._json_data[name] = json_data
        if self._editable:
            print(f"Adding entity {name} to {self._json_file}")
            with open(self._json_file, "w") as f:
                json.dump(self._json_data, f)
        self._invalidate_cache()
        return deepcopy(json_data)


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

        datatype_data = []
        seen_ids = set()
        last_date = None
        while True:
            if last_date is None:
                data = flexilims_session.get(datatype=datatype)
            else:
                data = flexilims_session.get(
                    datatype=datatype,
                    date_created=last_date,
                    date_created_operator="gt",
                )
            if not data:
                break
            new_items = [item for item in data if item["id"] not in seen_ids]
            for item in new_items:
                seen_ids.add(item["id"])
                datatype_data.append(item)
            if len(data) < 1000:
                break
            dates = [
                item.get("dateCreated")
                for item in data
                if item.get("dateCreated") is not None
            ]
            if not dates:
                break
            max_date = max(dates)
            if last_date is not None and max_date <= last_date:
                last_date = max_date + 1
            else:
                last_date = max_date

        if verbose:
            print(f"    ... {len(datatype_data)} {datatype} entities")
        all_data.extend(datatype_data)

    if verbose:
        print("Create JSON data")
    if not all_data:
        return {}

    entities_by_id = {}
    children_by_origin = defaultdict(list)
    roots = []
    for item in all_data:
        entry = deepcopy(item)
        if _is_missing_origin(entry.get("origin_id")):
            entry["origin_id"] = None
            roots.append(entry)
        else:
            children_by_origin[entry["origin_id"]].append(entry)
        entities_by_id[entry["id"]] = entry

    json_data = {}
    attached_ids = set()
    for root in roots:
        json_data[root["name"]] = root
        attached_ids.add(root["id"])
        _add_recursively(root, children_by_origin, attached_ids)

    omitted_count = len(entities_by_id) - len(attached_ids)
    if omitted_count > 0:
        logger.warning(
            "%d downloaded entities have an origin_id that is not in the "
            "downloaded types (or descend from one) and will be omitted from the "
            "hierarchy.",
            omitted_count,
        )
    return json_data


def _add_recursively(target, children_by_origin, attached_ids=None):
    """Recursively attach children from `children_by_origin` onto `target`."""
    assert "children" not in target, "Entity already has a `children` field"
    children = children_by_origin.get(target["id"])
    if not children:
        return target
    target["children"] = {}
    for child in children:
        target["children"][child["name"]] = child
        if attached_ids is not None:
            attached_ids.add(child["id"])
        _add_recursively(child, children_by_origin, attached_ids)
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
    import flexiznam as flz  # ty: ignore[unresolved-import]

    import flexilims as flm

    password = flz.config.config_tools.get_password(username="blota", app="flexilims")
    flexilims_session = flm.Flexilims(
        "blota", password=password, project_id="624ae21a73245b6d9992a1f5"
    )

    db = download_database(
        flexilims_session, ["mouse", "session", "recording", "dataset"]
    )
