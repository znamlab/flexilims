"""
Module to run FlexiLIMS in offline mode.

This will use a JSON file as a database instead of the online MongoDB.

Functions to generate the JSON are also included.
"""
from flexilims import main


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
