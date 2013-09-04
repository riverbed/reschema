# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import re

def parse_prop(obj, srcobj, prop, defaultValue=None, required=False, checkType=None):
    if prop in srcobj:
        val = srcobj[prop]
        del srcobj[prop]
        if checkType:
            if not isinstance(val, checkType):
                raise ValueError("Value provided for %s must be %s, got %s" % (prop, str(checkType), type(val)))

    elif required:
        raise ValueError("Missing required property '%s'" % prop)
    else:
        val = defaultValue
        
    if obj:
        setattr(obj, prop, val)

    return val

def a_or_an(s):
    if s[0] in ('a', 'e', 'i', 'o'):
        return "an"
    else:
        return "a"


def str_to_id(s, c='_'):
    """Convert the input string to a valid HTML id by replacing all invalid
    characters with the character C."""
    return (re.sub('[^a-zA-Z0-9-:.]', c, s)).strip('_')
