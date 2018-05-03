# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

#pylint: disable-all

# Inspired By Dag Sverre Seljebotn
# https://gist.github.com/dagss/5008118

# OrderedDict method inspired by
# http://stackoverflow.com/questions/5121931/
"""
A PyYAML loader that annotates position in source code and uses an OrderedDict.

The loader is based on `SafeConstructor`, i.e., the behaviour of
`yaml.safe_load`, but in addition:

 - Every dict/list/unicode is replaced with dict_node/list_node/unicode_node,
   which subclasses dict/list/unicode to add the attributes `start_mark`
   and `end_mark`. (See the yaml.error module for the `Mark` class.)

 - Every string is always returned as unicode, no ASCII-ficiation is
   attempted.

 - Note that int/bool/... are returned unchanged for now
"""
from yaml.composer import Composer
from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.resolver import Resolver
from yaml.parser import Parser
from yaml.constructor import SafeConstructor

from reschema.loader_nodes import (dict_node, list_node, str_node)


# Ordered so long as python 3.6+ is used.
class OrderedLoader(Reader, Scanner, Parser,
                   Composer, SafeConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

def ordered_load(stream):
    return OrderedLoader(stream).get_single_data()


class MarkedNodeConstructor(SafeConstructor):

    def construct_yaml_map(self, node):
        obj, = super().construct_yaml_map(node)
        return dict_node(obj, node.start_mark, node.end_mark)

    def construct_yaml_seq(self, node):
        obj, = super().construct_yaml_seq(node)
        return list_node(obj, node.start_mark, node.end_mark)

    def construct_yaml_str(self, node):
        gen = super().construct_scalar(node)
        node_data = ''.join(list(gen))
        return str_node(node_data, node.start_mark, node.end_mark)

MarkedNodeConstructor.add_constructor(
    'tag:yaml.org,2002:map', MarkedNodeConstructor.construct_yaml_map)

MarkedNodeConstructor.add_constructor(
    'tag:yaml.org,2002:seq', MarkedNodeConstructor.construct_yaml_seq)

MarkedNodeConstructor.add_constructor(
    'tag:yaml.org,2002:str', MarkedNodeConstructor.construct_yaml_str)


class MarkedLoader(Reader, Scanner, Parser,
                   Composer, MarkedNodeConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        MarkedNodeConstructor.__init__(self)
        Resolver.__init__(self)


def marked_load(stream):
    return MarkedLoader(stream).get_single_data()


def test_ordered_yaml():

    # note: test very sensitive to whitespace in string below
    d = ordered_load('''\
    a:
      [b, c, {d: e}]
    f:
      g: h''')

    assert d == {'a': ['b', 'c', {'d': 'e'}], 'f': {'g': 'h'}}

    assert isinstance(d['a'][2]['d'], str)
    assert isinstance(d, dict)
    assert isinstance(d['f'], dict)
    assert isinstance(d['a'], list)


def test_marked_yaml():
    def loc(obj):
        return (obj.start_mark.line, obj.start_mark.column,
                obj.end_mark.line, obj.end_mark.column)

    # note: test very sensitive to whitespace in string below
    d = marked_load('''\
    a:
      [b, c, {d: e}]
    f:
      g: h''')

    assert d == {'a': ['b', 'c', {'d': 'e'}], 'f': {'g': 'h'}}
    assert loc(d['a'][2]['d']) == (1, 17, 1, 18)
    assert loc(d) == (0, 4, 3, 10)
    assert loc(d['a']) == (1, 6, 1, 20)

    assert isinstance(d['a'][2]['d'], str)
    assert isinstance(d, dict)
    assert isinstance(d['f'], dict)
    assert isinstance(d['a'], list)


if __name__ == '__main__':
    test_ordered_yaml()
    test_marked_yaml()
