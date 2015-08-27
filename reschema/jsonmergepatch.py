# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
This module implements JSON merge-patch according to
http://tools.ietf.org/html/draft-ietf-appsawg-json-merge-patch-02

This implementation supports resolution of $ref/$merge
only when needed.

"""

import copy
import logging
import json

from reschema.parser import Parser
from reschema.exceptions import ParseError
import reschema.settings


logger = logging.getLogger(__name__)


def isdebug():
    return (reschema.settings.VERBOSE_DEBUG and
            logger.isEnabledFor(logging.DEBUG))


def _eval_shallow(servicedef, obj, need_copy=False):
    """Resolve $ref and $merge in obj, using servicedef for remote references.

    This function takes an input object which is a dictionary, and evaluates
    $merge / $ref only if they are present at the root of the object.

    If need_copy is True, a modifyable shallow copy is returned.

    """

    # _eval_shallow() resolves $ref and $merge to their values in
    # source and with_.  This is a *shallow* evaluation in that embedded
    # $ref or $merge at deeper levels are *not* resolved.
    #
    # For example, the following will be resolved:
    #    { $ref: ... }
    #    { $merge: ... }
    #
    # But the following will *not* be resolved
    #    { type: object,
    #      properties: { x: { $ref: ... } } }
    #
    # Need to loop in the event that a $ref resolves to another $ref
    # or a $ref to a $merge:
    #
    #    { $ref: <target1> } --> { $ref: <target2> } --> { <value2> }
    #

    # Minimize copies so that we don't bloat memory
    done = False
    is_copy = False
    while not done:
        if '$merge' in obj:
            with Parser(obj['$merge'], 'eval_shallow') as merge_parser:
                merge_source = merge_parser.parse('source', save=False,
                                                  required=True)
                merge_with = merge_parser.parse('with', save=False,
                                                required=True)

            # This always returns a copy
            obj = json_merge_patch(servicedef, merge_source, merge_with)
            is_copy = True

        elif '$ref' in obj:
            if len(obj.keys()) != 1:
                raise ParseError(
                    "$ref object may not have any other properties", obj)

            sch = servicedef.find(obj['$ref'])
            obj = sch.input
            is_copy = False

        else:
            done = True

    if not is_copy and need_copy:
        obj = copy.copy(obj)

    return obj


def json_merge_patch(servicedef, source, with_):
    """Return a new dict from source with with_ as a json-merge-patch. """

    if isinstance(source, list) or isinstance(with_, list):
        return with_

    if not isinstance(source, dict):
        raise TypeError('source must be a dict, got %s' % (type(source)))

    if not isinstance(with_, dict):
        raise TypeError('with_ must be a dict, got %s' % (type(with_)))

    isdebug() and logger.debug('JSON merge:\nsource = %s\nwith = %s' %
                               (json.dumps(source, indent=2),
                                json.dumps(with_, indent=2)))

    if (  '$ref' in source and
          '$ref' in with_ and
          source == with_):
        # If merging 2 $refs and they have the same target, nothing
        # to do ... but avoid infinite recusion!
        return source

    # Need to make a copy of source, as this is going to be modified
    # Only make a shallow copy here - only the shallow properties
    # are modified in this call.  Recursively deeper calls will make
    # deeper copies as needed.
    source = _eval_shallow(servicedef, source, need_copy=True)

    # with_ is only used in a readonly fashion, so no need to copy
    with_ = _eval_shallow(servicedef, with_, need_copy=False)

    for key, value in with_.iteritems():
        if value is None:
            # Remove the key if present in the source
            if key in source:
                del source[key]
        elif (  isinstance(value, dict) and
                key in source and
                isinstance(source[key], dict)):
            # If this key is a dict in both source and with_, recurse
            source[key] = json_merge_patch(servicedef, source[key], value)
        else:
            # Otherwise update the source for this key.  This may add the
            # key to source if it was not already present
            source[key] = value

    isdebug() and logger.debug('JSON merge result:\n%s' %
                               (json.dumps(source, indent=2)))

    return source
