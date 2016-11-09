# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re
from reschema.exceptions import ParseError

# copy params from previous uritemplate version
RESERVED = ":/?#[]@!$&'()*+,;="
OPERATOR = "+#./;?&|!@"
MODIFIER = ":^"
TEMPLATE = re.compile("{([^\}]+)}")


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


def uritemplate_required_variables(template):
    """Returns the set of vars in a uri template that are required.

    Query related variables are prefixed by ? or &:

       template = 'http://foo.bar/items/{id}?x={x}{&y,z}{#frag}'

    x, y, and z are considered query variables and will be skipped.

    """
    vars = set()
    for varlist in TEMPLATE.findall(template):
        if varlist[0] in "?&":
            continue
        if varlist[0] in OPERATOR:
            varlist = varlist[1:]
        varspecs = varlist.split(',')
        for var in varspecs:
            # handle prefix values
            var = var.split(':')[0]
            # handle composite values
            if var.endswith('*'):
                var = var[:-1]
            vars.add(var)
    return vars


def uritemplate_add_query_params(template, params):
    if not params:
        return template

    for varlist in TEMPLATE.findall(template):
        if varlist[0] in "?&":
            orig = varlist
            updated = orig + ',' + ','.join(params)
            return template.replace(orig, updated)

    return "%s{?%s}" % (template, ','.join(params))
