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
from collections import OrderedDict

import yaml
from yaml.composer import Composer
from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.resolver import Resolver
from yaml.parser import Parser
from yaml.constructor import SafeConstructor, ConstructorError

from reschema.loader_nodes import (dict_node, list_node, unicode_node,
                                   add_marks_to_node)


class OrderedNodeConstructor(SafeConstructor):
    # To support lazy loading, the original constructors first yield
    # an empty object, then fill them in when iterated. Due to
    # laziness we omit this behaviour (and will only do "deep
    # construction") by first exhausting iterators, then yielding
    # copies.
    def _construct_ordereddict(self, node):
        # Inspired by http://stackoverflow.com/questions/5121931/
        mapping = OrderedDict()
        yield mapping
        if not isinstance(node, yaml.MappingNode):
            raise ConstructorError("while constructing an ordered map",
                                   node.start_mark,
                                   ("expected a mapping node, but found %s" %
                                    node.id),
                                   node.start_mark)
        for key_node, value_node in node.value:
            key = self.construct_object(key_node)
            try:
                hash(key)
            except TypeError, exc:
                raise ConstructorError('while constructing a mapping',
                                       node.start_mark,
                                       'found unacceptable key (%s)' % exc,
                                       key_node.start_mark)
            value = self.construct_object(value_node)
            mapping[key] = value

    def construct_yaml_omap(self, node):
        obj, = self._construct_ordereddict(node)
        return obj

OrderedNodeConstructor.add_constructor(
    'tag:yaml.org,2002:map', OrderedNodeConstructor.construct_yaml_omap)


class OrderedLoader(Reader, Scanner, Parser,
                   Composer, OrderedNodeConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

def ordered_load(stream):
    return OrderedLoader(stream).get_single_data()


class MarkedNodeConstructor(OrderedNodeConstructor):

    def construct_yaml_omap(self, node):
        obj, = self._construct_ordereddict(node)
        add_marks_to_node(obj, node.start_mark, node.end_mark)
        return obj

    def construct_yaml_map(self, node):
        obj, = SafeConstructor.construct_yaml_map(self, node)
        return dict_node(obj, node.start_mark, node.end_mark)

    def construct_yaml_seq(self, node):
        obj, = SafeConstructor.construct_yaml_seq(self, node)
        return list_node(obj, node.start_mark, node.end_mark)

    def construct_yaml_str(self, node):
        obj = SafeConstructor.construct_scalar(self, node)
        return unicode_node(obj, node.start_mark, node.end_mark)

MarkedNodeConstructor.add_constructor(
    'tag:yaml.org,2002:map', MarkedNodeConstructor.construct_yaml_omap)

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
        SafeConstructor.__init__(self)
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
