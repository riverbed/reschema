# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.
"""
This module implements JSON merge-patch according to
http://tools.ietf.org/html/draft-ietf-appsawg-json-merge-patch-02

This implementation supports resolution of $ref/$merge
only when needed.

"""

import copy

from reschema.parser import Parser
from reschema.exceptions import ParseError


def resolve_refs(servicedef, obj):
    """Resolve $ref and $merge in obj, using servicedef for remote references."""

    need_copy = True
    while True:
        if '$merge' in obj:
            with Parser(obj['$merge'], 'resolve_refs') as merge_parser:
                merge_source = merge_parser.parse('source', save=False,
                                                  required=True)
                merge_with = merge_parser.parse('with', save=False,
                                                required=True)

            obj = json_merge_patch(servicedef, merge_source, merge_with)

            # json_merge_patch always returns a new object, so
            # no copy needed
            need_copy = False

        elif '$ref' in obj:
            if len(obj.keys()) != 1:
                raise ParseError(
                    "$ref object may not have any other properties", obj)

            sch = servicedef.find(obj['$ref'])
            obj = sch.input
            # Don't copy here -- if more references need resolving
            # a copy may be made elsewhere
            need_copy = True

        else:
            break

    if need_copy:
        return copy.copy(obj)

    return obj


def json_merge_patch(servicedef, source, merge):
    """Return a new dict from source with merge as a json-merge-patch.

    :param source: input object

    :param merge: merge object

    """

    if isinstance(source, list) or isinstance(merge, list):
        return merge

    if not isinstance(source, dict):
        raise TypeError('source must be a dict, got %s' % (type(source)))

    if not isinstance(merge, dict):
        raise TypeError('merge must be a dict, got %s' % (type(merge)))

    source = resolve_refs(servicedef, source)

    for key, value in merge.iteritems():
        if value is None:
            # Remove the key if present in the source
            if key in source:
                del source[key]
        elif (  isinstance(value, dict) and
                key in source and
                isinstance(source[key], dict)):
            # If this key is a dict in both source and merge, recurse
            source[key] = json_merge_patch(servicedef, source[key], value)
        else:
            # Otherwise update the source for this key.  This may add the
            # key to source if it was not already present
            source[key] = value
    return source
