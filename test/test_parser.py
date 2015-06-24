# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import copy

import pytest
import mock

from reschema.parser import Parser
from reschema.exceptions import ParseError


ID_HOSTNAME = 'http://support.riverbed.com'
ID_BASE = '%s/apis/testschema/1.0' % ID_HOSTNAME
ID_FRAGMENT = '#/foo/bar'
ID_ABSPATH = '/apis/otherschema/2.0'
ID_ABSPATH_FRAGMENT = '%s%s' % (ID_ABSPATH, ID_FRAGMENT)

INPUT_DICT = {
    'foo': 42,
    'bar': {'$ref': ID_FRAGMENT},
}

INPUT_LIST = ['foo', {'$ref': ID_FRAGMENT}]
INPUT_LIST_EXPANDED = ['foo', {'$ref': '%s%s' % (ID_BASE, ID_FRAGMENT)}]

ANY_NAME = 'whatever'
ANY_OBJ = {'stuff', 'nonsense'}


@pytest.fixture
def parser():
    p = Parser(INPUT_DICT, ANY_NAME)
    return p


def test_parser_dict_only():
    with pytest.raises(ParseError):
        Parser(INPUT_LIST, ANY_NAME)

    with pytest.raises(ParseError):
        Parser(INPUT_LIST, '{"foo": "bar"}')


def test_parser_context():
    with mock.patch('reschema.parser.Parser.set_context'):
        p = Parser(INPUT_DICT, ANY_NAME, ANY_OBJ)
        assert p.set_context.called_once_with(ANY_NAME, ANY_OBJ)


def test_set_context(parser):
    other_name = 'different_from_any_name'
    p = Parser(INPUT_DICT, ANY_NAME)
    p.mark_object = mock.Mock()
    p.set_context(other_name, ANY_OBJ)

    assert p.name == other_name
    assert p.obj is ANY_OBJ
    assert p.mark_object.called_once_with(ANY_OBJ)


def test_local_ref():
    assert Parser.expand_ref(
        ID_BASE, ID_FRAGMENT) == '%s%s' % (ID_BASE, ID_FRAGMENT)


def test_provider_ref():
    expanded = Parser.expand_ref(ID_BASE, ID_ABSPATH_FRAGMENT)
    assert expanded == '%s%s' % (ID_HOSTNAME, ID_ABSPATH_FRAGMENT)


def test_full_ref():
    id_ = '%s%s' % (ID_HOSTNAME, ID_ABSPATH_FRAGMENT)
    assert Parser.expand_ref(ID_BASE, id_) == id_


def test_expand_refs_empty_input():
    # Shouldn't raise an exception, nothing else to check.
    Parser.expand_refs(ID_BASE, None)

    input_ = {}
    Parser.expand_refs(ID_BASE, input_)
    assert input_ == {}


def test_expanded_refs_array():
    # This ends up covering the dict case as well, since the $ref must
    # be a dict itself.
    input_ = copy.deepcopy(INPUT_LIST)
    Parser.expand_refs(ID_BASE, input_)
    assert input_ == INPUT_LIST_EXPANDED


def test_preprocess():
    with mock.patch('reschema.parser.Parser.expand_refs'):
        Parser.preprocess(ID_BASE, copy.deepcopy(INPUT_LIST))
        Parser.expand_refs.assert_called_once_with(ID_BASE, INPUT_LIST)


def test_preprocess_input(parser):
    with mock.patch('reschema.parser.Parser.preprocess'):
        parser.preprocess_input(ID_BASE)
        parser.preprocess.assert_called_once_with(ID_BASE, parser.input)
