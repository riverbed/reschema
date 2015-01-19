# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import collections

import pytest
import mock

from reschema.exceptions import ParseError
from reschema.jsonschema import Path

TEMPLATE_BASE = '$/foos/items/{id}'
TEMPLATE_QUERY_ALL = '{?x,y,z,w}'
TEMPLATE_QUERY_TRAILING = '?x={stuff}{&y,z,w}'
TEMPLATE_FRAGMENT = '#/doesnt/matter'

PATH_NO_QUERY = TEMPLATE_BASE

PATH_WITH_QUERY = {
    'template': TEMPLATE_BASE + TEMPLATE_QUERY_ALL,
    'vars': {
        'x': '0/stuff',
        'w': {'type': 'integer'},
    },
}

PARAMS_DISJOINT = collections.OrderedDict([
    ('a', {'type': 'integer'}),
    ('b', {'type': 'string'}),
])

PARAMS_DISJOINT_TEMPLATE_ALL = '{?a,b}'
PARAMS_DISJOINT_TEMPLATE_TRAILING = '{&a,b}'

PARAMS_OVERLAP = collections.OrderedDict([
    ('a', {'type': 'integer'}),
    ('w', {'type': 'integer'}),
    ('x', {'type': 'string'}),
    ('z', {'type': 'number'}),
])

PARAMS_CONFLICT = {
    'w': {'type': 'string'},
}

ANY_LINK_ID = '/resourcename/link/whatever'


@pytest.yield_fixture
def link():
    link = mock.Mock()
    link.fullname.return_value = 'fullname'
    link.id = ANY_LINK_ID

    # Also, we need to patch this sometime, not worth a separate fixture.
    with mock.patch('reschema.jsonschema.Schema.parse',
                    return_value=mock.Mock()):
        yield link


@pytest.fixture
def path(link):
    p = Path(link, PATH_WITH_QUERY)
    return p


@pytest.fixture
def path_no_query(link):
    p = Path(link, PATH_NO_QUERY)
    return p


def test_split_base_only(link):
    p = Path(link, TEMPLATE_BASE)
    assert p.split_template() == (TEMPLATE_BASE, '', '')


def test_split_query_all(link):
    p = Path(link, TEMPLATE_BASE + TEMPLATE_QUERY_ALL)
    assert p.split_template() == (TEMPLATE_BASE, TEMPLATE_QUERY_ALL, '')


def test_base_fragment(link):
    p = Path(link, TEMPLATE_BASE + TEMPLATE_FRAGMENT)
    assert p.split_template() == (TEMPLATE_BASE, '', TEMPLATE_FRAGMENT)


def test_query_trailing_with_fragment(link):
    p = Path(link,
             TEMPLATE_BASE + TEMPLATE_QUERY_TRAILING + TEMPLATE_FRAGMENT)
    assert p.split_template() == (
        TEMPLATE_BASE, TEMPLATE_QUERY_TRAILING, TEMPLATE_FRAGMENT)


def test_conflicts_no_conflicts(path):
    assert path._handle_param_conflicts(PARAMS_DISJOINT) == PARAMS_DISJOINT


@pytest.mark.xfail(raises=NotImplementedError)
def test_conflicts_with_overlap(path):
    expected = PATH_WITH_QUERY['vars'].copy()
    expected.update(PARAMS_DISJOINT)
    assert path._handle_param_conflicts(PARAMS_OVERLAP) == expected


@pytest.mark.xfail(raises=NotImplementedError)
def test_conflicts_with_conflicts(path):
    with pytest.raises(ParseError):
        path._handle_param_conflicts(PARAMS_CONFLICT)


def test_apply_all_params(path_no_query):
    base, query, fragment = path_no_query.split_template()
    path_no_query._apply_params(PARAMS_DISJOINT)

    assert path_no_query.split_template() == (
        base, PARAMS_DISJOINT_TEMPLATE_ALL, fragment)


def test_apply_trailing_params(path):
    base, query, fragment = path.split_template()
    path._apply_params(PARAMS_DISJOINT)

    assert path.split_template() == (
        base, query + PARAMS_DISJOINT_TEMPLATE_TRAILING, fragment)
