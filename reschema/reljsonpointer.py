# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

"""
This module implements relative JSON pointers that take the form '<num>/<jsonpointer>'.
A relative JSON pointer is resolved against a data object and a base pointer.
"""

import jsonpointer
from jsonpointer import JsonPointer, JsonPointerException


class RelJsonPointer(JsonPointer):
    def __init__(self, basepointer, relpointer):
        if basepointer is None:
            basepointer = ''
        JsonPointer.__init__(self, basepointer)

        try:
            uplevels = int(relpointer)
            relparts = []

        except:
            try:
                (uplevels, relpath) = relpointer.split('/', 1)
                uplevels = int(uplevels)
                if uplevels < 0:
                    raise JsonPointerException()
            except:
                raise JsonPointerException("Invalid relative pointer '%s', "
                                           "expected '<int>/<pointer>" % relpointer)

            if uplevels > len(self.parts):
                raise JsonPointerException("Base pointer '%s' is not deep enough for " 
                                           "relative pointer '%s' levels" %
                                           (basepointer, relpointer))
            relparts = JsonPointer('/' + relpath).parts
            
        if uplevels > 0:
            self.parts = self.parts[0:-uplevels]

        self.parts.extend(relparts)


def resolve_rel_pointer(doc, pointer, relpointer, default=jsonpointer._nothing):
    """
    Resolves a relative pointer against doc and pointer

    >>> obj = {'foo': {'anArray': [ {'prop': 44}], 'another prop': {'baz': 'A string' }}}

    >>> resolve_rel_pointer(obj, '/foo', '1') == obj
    True

    >>> resolve_rel_pointer(obj, '/foo/anArray', '1') == obj['foo']
    True

    >>> resolve_rel_pointer(obj, '/foo/anArray', '1/another%20prop') == obj['foo']['another prop']
    True

    >>> resolve_rel_pointer(obj, '/foo/anArray', '1/another%20prop/baz') == obj['foo']['another prop']['baz']
    True

    >>> resolve_pointer(obj, '/foo/anArray/0') == obj['foo']['anArray'][0]
    True

    """

    op = RelJsonPointer(pointer, relpointer)
    return op.resolve(doc, default)
