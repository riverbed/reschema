# Copyright (c) 2013-2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

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


def a_or_an(s):
    if s[0] in ('a', 'e', 'i', 'o', 'u'):
        return "an"
    else:
        return "a"


def str_to_id(s, c='_'):
    """Convert the input string to a valid HTML id by replacing all invalid
    characters with the character C."""
    return (re.sub('[^a-zA-Z0-9-:.]', c, s)).strip('_')
