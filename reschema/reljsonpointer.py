# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
This module implements relative JSON pointers that take the form '<num>/<jsonpointer>'.
A relative JSON pointer is resolved against a data object and a base pointer.
"""

import re
import jsonpointer
from jsonpointer import JsonPointer, JsonPointerException


num_re = re.compile('^[0-9]+$')
num_hash_re = re.compile('^[0-9]+#$')
num_rel_re = re.compile('^[0-9]+/')

class RelJsonPointer(JsonPointer):
    def __init__(self, basepointer, relpointer):
        if basepointer is None:
            basepointer = ''
        super(RelJsonPointer, self).__init__(basepointer)

        self.isHash = False

        if num_re.match(relpointer):
            uplevels = int(relpointer)
            relparts = []

        elif num_hash_re.match(relpointer):
            uplevels = int(relpointer[:-1])
            relparts = []
            self.isHash = True

        elif num_rel_re.match(relpointer):
            (uplevels, relpath) = relpointer.split('/', 1)
            uplevels = int(uplevels)

            relparts = JsonPointer('/' + relpath).parts

        else:
            raise JsonPointerException(
                "Invalid relative JSON pointer '%s', " % relpointer)

        if uplevels > 0:
            if uplevels > len(self.parts):
                raise JsonPointerException(
                    "Base pointer '%s' is not deep enough for "
                    "relative pointer '%s' levels" % (basepointer, relpointer))
            self.parts = self.parts[0:-uplevels]

        if self.isHash and len(self.parts) == 0:
            raise JsonPointerException(
                "Cannot use '#' at root of relative JSON pointer '%s', "
                % relpointer)

        self.parts.extend(relparts)

    def resolve(self, doc, default=jsonpointer._nothing):
        if self.isHash:
            if len(self.parts) == 1:
                refdata = doc
            else:
                p = JsonPointer('/' + '/'.join(self.parts[:-1]))
                refdata = p.resolve(doc)
            if isinstance(refdata, list):
                return int(self.parts[-1])
            else:
                return self.parts[-1]
        else:
            return super(RelJsonPointer, self).resolve(doc, default)

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
