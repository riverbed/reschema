# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import json
from collections import OrderedDict

from yaml.error import Mark
from json.scanner import py_make_scanner
import json.decoder

from reschema.loader_nodes import ordered_dict_node, list_node, unicode_node


def linecol(doc, pos):
    # assume zero-indexed
    lineno = doc.count('\n', 0, pos)
    if lineno == 0:
        colno = pos - 1
    else:
        colno = pos - doc.rindex('\n', 0, pos) - 1
    return lineno, colno


class Decoder(json.decoder.JSONDecoder):
    def __init__(self, name="", *args, **kwargs):
        super(Decoder, self).__init__(*args, **kwargs)

        def wrap_obj_parser(parser, node_type):
            def internal(o_and_start, *args, **kwargs):
                o, start = o_and_start
                r, end = parser(o_and_start, *args, **kwargs)

                start_line, start_col = linecol(o, start)
                end_line, end_col = linecol(o, end)
                start_mark = Mark(name, start, start_line, start_col, o, start)
                end_mark = Mark(name, end, end_line, end_col, o, start)

                return node_type(r, start_mark, end_mark), end
            return internal

        def wrap_parser(parser, node_type):
            def internal(o, start, *args, **kwargs):
                r, end = parser(o, start, *args, **kwargs)

                start_line, start_col = linecol(o, start)
                end_line, end_col = linecol(o, end)
                start_mark = Mark(name, start, start_line, start_col, o, start)
                end_mark = Mark(name, end, end_line, end_col, o, start)

                return node_type(r, start_mark, end_mark), end
            return internal

        self.parse_string = wrap_parser(self.parse_string, unicode_node)
        self.parse_array = wrap_obj_parser(self.parse_array, list_node)
        self.parse_object = wrap_obj_parser(self.parse_object,
                                            ordered_dict_node)

        # Not thread safe, but need to patch this for loading marks onto object
        # keys.
        json.decoder.scanstring = self.parse_string

        # Need to hook the python scanner because the C scanner doesn't have
        # a hookable method to parse_string.
        self.scan_once = py_make_scanner(self)


def marked_load(stream):
    return json.load(stream, cls=Decoder, name=stream.name)


def clean_load(stream):
    return json.load(stream, object_pairs_hook=OrderedDict)
