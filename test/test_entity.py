# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import mock
import pytest

from reschema import jsonschema


ANY_NAME = 'foo'
ANY_PARENT_NAME = 'bar'
ANY_ID = '#/resources/foo'
ANY_SERVICEDEF_ID = 'http://support.riverbed.com/apis/mock/1.0'

ANY_INTERMEDIARY = 'inter'
ANY_INPUT = {'blah': 'whatever'}

MOCK_SERVICEDEF = mock.Mock()
MOCK_SERVICEDEF.id = ANY_SERVICEDEF_ID
MOCK_SERVICEDEF.fullid.return_value = ANY_SERVICEDEF_ID

MOCK_PARENT = mock.Mock()
MOCK_PARENT.name = ANY_PARENT_NAME
MOCK_PARENT.fullname.return_value = ANY_PARENT_NAME
MOCK_PARENT.servicedef = MOCK_SERVICEDEF

ANY_FULL_ID = '/'.join((MOCK_SERVICEDEF.id, ANY_ID))


@pytest.fixture
def e_parent_only():
    e = jsonschema.Entity(id=ANY_ID,
                          name=ANY_NAME,
                          parent=MOCK_PARENT)
    return e


def test_init_parent_only(e_parent_only):
    assert e_parent_only.id == ANY_ID
    assert e_parent_only.name == ANY_NAME
    assert e_parent_only.parent is MOCK_PARENT
    assert e_parent_only.servicedef is MOCK_SERVICEDEF


def test_repr(e_parent_only):
    assert repr(e_parent_only) == "<servicedef.%s '%s'>" % (
        jsonschema.Entity.__name__, e_parent_only.fullid())


def test_absolute_id(e_parent_only):
    assert e_parent_only.fullid() == MOCK_SERVICEDEF.id + ANY_ID


def test_relative_id(e_parent_only):
    assert e_parent_only.fullid(True) == ANY_ID


# fullname() was originally defined separately in many places, hence the
# various specific unit tests.  The behaviors should continue with the
# base class Entity

def test_name_schema_no_parent():
    e = jsonschema.Entity(id=ANY_ID, name=ANY_NAME,
                          servicedef=MOCK_SERVICEDEF)
    assert e.fullname() == e.name


def test_name_no_parent_no_name():
    unnamed_parent = mock.Mock()
    unnamed_parent.servicedef = MOCK_SERVICEDEF
    unnamed_parent.fullname.return_value = None

    e = jsonschema.Entity(id=ANY_ID, name=None, parent=unnamed_parent)
    assert e.fullname() is None


def test_name_schema_parent_unnamed():
    unnamed_parent = mock.Mock()
    unnamed_parent.servicedef = MOCK_SERVICEDEF
    unnamed_parent.fullname.return_value = None

    e = jsonschema.Entity(id=ANY_ID, name=ANY_NAME, parent=unnamed_parent)
    assert e.fullname() == e.name


def test_name_schema_parent_named(e_parent_only):
    e = e_parent_only
    assert e.fullname() == '%s.%s' % (e.parent.fullname(), e.name)


def test_name_schema_parent_array():
    array = mock.Mock(spec=jsonschema.Array, instance=True)
    array.fullname.return_value = ANY_PARENT_NAME
    array.servicedef = MOCK_SERVICEDEF
    e = jsonschema.Entity(id=ANY_ID, name=ANY_NAME, parent=array)
    assert e.fullname() == '%s[%s]' % (e.parent.fullname(), e.name)


def test_name_intermediary():
    e = jsonschema.Entity(id=ANY_ID, name=ANY_NAME, parent=MOCK_PARENT,
                          intermediary=ANY_INTERMEDIARY)
    assert e.fullname() == '%s.%s.%s' % (ANY_PARENT_NAME,
                                         ANY_INTERMEDIARY,
                                         ANY_NAME)
