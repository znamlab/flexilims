"""Utility functions useful for both online and offline FlexiLIMS."""

import math
import re
import warnings

import pandas as pd

SPECIAL_CHARACTERS = re.compile(r'[\',\.@"+=\-!#$%^&*<>?/\|}{~:]')


class FlexilimsError(Exception):
    """Error in flexilims code"""

    pass


class AuthenticationError(Exception):
    """Error 403 when authenticating"""

    pass


def check_flexilims_validity(attributes, warn_case=False):
    """Check that the data can be uploaded to flexilims

    - Remove None
    - Warn if attributes have white characters
    - Crashing if attributes have special characters
    - [optionally] Warn if attributes are not lowercase. This is a minor display issue
        attributes defined in the lab design page will always be displayed with the
        same case.

    Args:
        attributes: dictionary to check
        warn_case: if True, warn if attribute names are not lowercase

    Returns:
        None
    """
    _replace_nones(attributes)
    for attr_name in attributes:
        if not attr_name.islower() and warn_case:
            warnings.warn(
                "Warning. Attribute names are not case sensitive on the UI."
                " `%s` might not appear online" % attr_name
            )
        if r"\s" in attr_name:
            warnings.warn(
                "Warning. Attribute names should not contain white "
                "characters. `%s` might not appear online" % attr_name
            )

        if SPECIAL_CHARACTERS.search(attr_name) is not None:
            raise FlexilimsError(
                "Attribute names cannot contain special "
                "characters. `%s` is invalid" % attr_name
            )


def _replace_nones(attributes):
    """Remove None in attributes

    None are not json compatible. To upload a non you need to upload an empty
    structure (either a list or a dict)

    Args:
        attributes: dictionary to clean (in place)

    Returns:
        None
    """

    for k, v in attributes.items():
        if isinstance(v, tuple):
            # make sure we have list to do in-place modification
            v = list(v)
            attributes[k] = v
        if isinstance(v, dict):
            _replace_nones(v)
        elif isinstance(v, list):
            _cleanlist(v)
        # we might have an empty dictionary or empty list
        if hasattr(v, "__iter__") and (not isinstance(v, str)) and (not len(v)):
            print(
                "Warning: %s is an empty structure and will be uploaded as `None`" % k
            )
        if v is None:
            print("Setting `%s` to None. Reply will contain an empty list" % k)
            attributes[k] = []
        elif isinstance(v, float) and math.isnan(v):
            print("Setting `%s` to None. Reply will contain an empty list" % k)
            attributes[k] = []


def _cleanlist(list2clean):
    """Check recursively if the list contains None or dict and replace them

    Args:
        list2clean: a list of elements

    Returns:
        None (changes in place)

    """
    for index, element in enumerate(list2clean):
        if isinstance(element, tuple):
            element = list(element)
            list2clean[index] = element
        if isinstance(element, list):
            _cleanlist(element)
        elif isinstance(element, dict):
            _replace_nones(element)
        elif element is None:
            print("Setting a list element to None. Reply will contain an empty list")
            list2clean[index] = []
    assert all([e is not None for e in list2clean])


def format_results(results):
    """Make request output a nice DataFrame

    This will crash if any attribute is also present in the flexilims reply,
    i.e. if an attribute is named:
    'id', 'type', 'name', 'incrementalId', 'createdBy', 'dateCreated',
    'origin_id', 'objects', 'customEntities', or 'project'

    Args:
        results (:obj:`list` of :obj:`dict`): Flexilims reply

    Returns:
        :py:class:`pandas.DataFrame`: Reply formatted as a DataFrame

    """
    for result in results:
        for attr_name, attr_value in result["attributes"].items():
            if attr_name in result:
                raise FlexilimsError(
                    "An entity should not have %s as attribute" % attr_name
                )
            result[attr_name] = attr_value
        result.pop("attributes")
    return pd.DataFrame(results)
