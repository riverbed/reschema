# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import re

from reschema.exceptions import ParseError


def check_type(prop, val, valid_type, obj=None):
    if type(valid_type) is not list:
        valid_type = [valid_type]

    valid = False
    for t in valid_type:
        if isinstance(val, t):
            valid = True
            break

    if not valid:
        msg = ("Value provided for '%s' must be %s, got %s" %
               (prop, str(valid_type), type(val)))
        raise ParseError(msg, prop, obj)


def parse_prop(obj, srcobj, prop,
               default_value=None, required=False, valid_type=None):
    """Parse and remove a key from a dict and make it a property on an object.

    The property is removed from the source object, even if an exception
    is raised during parsing.

    :param obj: A Python object instance on which properties will be created.
                This can be None, in which case it is ignored.
    :type obj: object instance
    :param srcobj: The dict in which the object may be found.
    :type srcobj: dict
    :param prop: The dictionary key name of the property.
    :type prop: string
    :param default_value: A value to use if the property is missing
                          but not required.  Ignored if `required` is True.
    :param required: Causes ParseError to be raised if `prop` is not in `obj`.
    :type required: boolean
    :param valid_type: verifies that the property value is an instance of at
                       least one of the types passed in this parameter.
    :type valid_type: type or list of types

    :raises reschema.exceptions.ParseError: if the type of the data
      is incorrect or if the property is required but missing.

    :return: The parsed value.
    """
    if prop in srcobj:
        val = srcobj[prop]
        if valid_type:
            check_type(prop, val, valid_type, srcobj)
        del srcobj[prop]

    elif required:
        raise ParseError("Missing required property '%s'" % prop, srcobj)
    else:
        val = default_value

    if obj is not None:
        setattr(obj, prop, val)

    return val


def a_or_an(s):
    if s[0] in ('a', 'e', 'i', 'o', 'u'):
        return "an"
    else:
        return "a"


def str_to_id(s, c='_'):
    """Convert the input string to a valid HTML id by replacing all invalid
    characters with the character C."""
    return (re.sub('[^a-zA-Z0-9-:.]', c, s)).strip('_')
