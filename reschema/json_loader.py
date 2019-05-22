# Copyright (c) 2019 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import json
from io import StringIO
from yaml.error import Mark
from json.scanner import py_make_scanner
import json.decoder

from reschema.loader_nodes import dict_node, list_node, str_node


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
        super().__init__(*args, **kwargs)

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

        self.parse_string = wrap_parser(self.parse_string, str_node)
        self.parse_array = wrap_obj_parser(self.parse_array, list_node)
        self.parse_object = wrap_obj_parser(self.parse_object, dict_node)

        # Not thread safe, but need to patch this for loading marks onto object
        # keys.
        json.decoder.scanstring = self.parse_string

        # Need to hook the python scanner because the C scanner doesn't have
        # a hookable method to parse_string.
        self.scan_once = py_make_scanner(self)


def marked_load(stream):
    return json.load(stream, cls=Decoder)

def clean_load(stream):
    return json.load(stream)


test_json_str = '''\
{
    "a": [
        "b",
        "c",
        {
            "d": "e"
        }
    ],
    "f": {
        "g": "h"
    }
}'''


def test_clean_load():

    # note: test very sensitive to whitespace in string below
    d = clean_load(StringIO(test_json_str))

    assert d == {'a': ['b', 'c', {'d': 'e'}], 'f': {'g': 'h'}}

    assert isinstance(d['a'][2]['d'], str)
    assert isinstance(d, dict)
    assert isinstance(d['f'], dict)
    assert isinstance(d['a'], list)


def test_marked_load():
    def loc(obj):
        return (obj.start_mark.line, obj.start_mark.column,
                obj.end_mark.line, obj.end_mark.column)

    # note: test very sensitive to whitespace in string below
    d = marked_load(StringIO(test_json_str))

    assert d == {'a': ['b', 'c', {'d': 'e'}], 'f': {'g': 'h'}}
    assert loc(d['a'][2]['d']) == (5, 18, 5, 20)
    assert loc(d) == (0, 0, 11, 1)
    assert loc(d['a']) == (1, 10, 7, 5)

    assert isinstance(d['a'][2]['d'], str)
    assert isinstance(d, dict)
    assert isinstance(d['f'], dict)
    assert isinstance(d['a'], list)


if __name__ == '__main__':
    test_clean_load()
    test_marked_load()
