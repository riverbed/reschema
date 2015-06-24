# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import print_function

import os
import logging
import unittest

import reschema
from reschema.lint import Validator, Result

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yaml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yaml')

SERVICE_DEF_TEMPLATE = '''
$schema: http://support.riverbed.com/apis/service_def/2.2
id: http://support.riverbed.com/apis/test/1.0
provider: riverbed
name: test
version: '1.0'
tags: {}
'''


def create_servicedef(fragment):
    """
    Parse a schema fragment and create a ServiceDef instance that can be
    passed to the Validator.

    The fragment should be from an outermost section of a servicedef file, eg
    "types:
       test:
         type: integer"

    The fragment will be merged into a template servicedef instance; any keys
    in the fragment override/are added to the template.

    :param fragment: Schema fragment to merge in
    :return: TestValidator
    """
    sdef = reschema.ServiceDef.create_from_text(SERVICE_DEF_TEMPLATE +
                                                fragment,
                                                format='yaml')

    return sdef


class TestLintBase(unittest.TestCase):
    """
    Helper class to run and validate relint calls
    """

    def check_result(self, rule_id, obj_id, result, fragment):
        """
        Verifies that relint declares  on the given fragment

        :param rule_id: Rule to verify passed
        :param obj_id: Object to verify rule passed on
        :param result: Test result expected
        :param fragment: fragment to check
        """

        sdef = create_servicedef(fragment)
        validator = Validator()
        results = validator.run(sdef)

        found_result = None
        for r in results:
            if (r.rule_id == rule_id) and (r.obj_id == obj_id):
                found_result = r
                break

        self.assertTrue(found_result,
                        'No result for {} on {} found'.format(rule_id, obj_id))
        self.assertEqual(found_result.status, result,
                         'Unexpected {}'.format(found_result))


class TestRelintDisable(TestLintBase):
    """
    Collection of tests that verify the relint-disable handling
    """

    def test_servicedef_disable(self):
        """
        Verifies top-level servicedef checks honor disable
        """
        self.check_result('W0002',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.DISABLED,
                          'tags:\n'
                          '   relint-disable: [ W0002 ] ')

    def test_resource_disable(self):
        """
        Verifies resource-level checks can be disabled
        """

        # Tag disable at the top level
        self.check_result('C0003', '#/resources/foo_resource', Result.DISABLED,
                          'tags:\n'
                          '   relint-disable: [ C0003 ]\n'
                          '\n'
                          'resources:\n'
                          '  foo_resource:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }')

        # Tag disable on the resource
        self.check_result('C0003', '#/resources/foo_resource', Result.DISABLED,
                          'resources:\n'
                          '  foo_resource:\n'
                          '    tags:\n'
                          '       relint-disable: [ C0003 ]\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }')

        # Tag disable on the sub-schema of resource
        self.check_result('C0001', '#/resources/foo_resource/properties/name',
                          Result.DISABLED,
                          'resources:\n'
                          '  foo_resource:\n'
                          '    tags:\n'
                          '       relint-disable: [ C0001 ]\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      name:\n'
                          '        type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }')

    def test_type_disable(self):
        """
        Verifies type-level checks can be disabled
        """

        # Tag disable at the top level
        self.check_result('C0002', '#/types/foo_type', Result.DISABLED,
                          'tags:\n'
                          '   relint-disable: [ C0002 ]\n'
                          '\n'
                          'types:\n'
                          '  foo_type:\n'
                          '    type: string')

        # Tag disable on the type
        self.check_result('C0002', '#/types/foo_type', Result.DISABLED,
                          'types:\n'
                          '  foo_type:\n'
                          '    tags:\n'
                          '       relint-disable: [ C0002 ]\n')

        # test disable on the sub-schema of type
        self.check_result('C0002', '#/types/foo_type/properties/name',
                          Result.DISABLED,
                          'types:\n'
                          '  foo_type:\n'
                          '    tags:\n'
                          '       relint-disable: [ C0002 ]\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      name: {type: string}\n')

    def test_link_disable(self):
        """
        Verifies link-level checks can be disabled
        """

        # Tag disable at the top level
        self.check_result('C0004', '#/resources/foo/links/foo_link',
                          Result.DISABLED,
                          'tags:\n'
                          '   relint-disable: [ C0004 ]\n'
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      foo_link:\n'
                          '        path: /foo/nope\n'
                          '        method: GET')

        # Tag disable on the resource
        self.check_result('C0004', '#/resources/foo/links/foo_link',
                          Result.DISABLED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    tags:\n'
                          '       relint-disable: [ C0004 ]\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      foo_link:\n'
                          '        path: /foo/nope\n'
                          '        method: GET')

        # Tag disable on the link
        self.check_result('C0004', '#/resources/foo/links/foo_link',
                          Result.DISABLED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      foo_link:\n'
                          '        path: /foo/nope\n'
                          '        method: GET\n'
                          '        tags:\n'
                          '           relint-disable: [ C0004 ]')

        # test disable on the subschema of link
        self.check_result('C0005',
                          '#/resources/foo/links/link1/request/properties/p1',
                          Result.DISABLED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      link1:\n'
                          '        path: /foo/nope\n'
                          '        method: GET\n'
                          '        tags:\n'
                          '           relint-disable: [ C0005 ]\n'
                          '        request:\n'
                          '          type: object\n'
                          '          properties:\n'
                          '            p1: { type: number }')


class TestRelint(TestLintBase):
    def test_rule_W0001(self):
        ''' The ``provider`` field must be set to ``riverbed`` '''

        self.check_result('W0001',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'provider: riverbed\n')

        self.check_result('W0001',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'provider: wrong_provider\n')

    def test_rule_W0002(self):
        ''' The ``id`` field must be
        ``http://support.riverbed.com/apis/{name}/{version}`` '''

        self.check_result('W0002',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test')

        self.check_result('W0002',
                          'http://support.riverbed.com/apis/wrongid/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/wrongid/1.0\n'
                          'name: test')

        self.check_result('W0002',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: wrongname')

    def test_rule_W0003(self):
        ''' the schema field must be set to
            http://support.riverbed.com/apis/service_def/{version}
        '''
        self.check_result('W0003',
                          'http://support.riverbed.com/apis/service_def/2.2',
                          Result.PASSED,
                          "$schema: "
                          "http://support.riverbed.com/apis/service_def/2.2\n"
                          'id: '
                          'http://support.riverbed.com/apis/service_def/2.2\n'
                          'name: test\n')

    def test_rule_W0004(self):
        ''' the schema must have a title '''

        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'title: test_relint\n')

        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'title: \n')

        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test\n')

    def test_rule_W0005(self):
        '''additionalProperties required for Object schema'''
        self.check_result('W0005', '#/resources/info',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    additionalProperties : False\n')

        self.check_result('W0005', '#/resources/info',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n')

    def test_rule_C0001(self):
        '''name should start with a letter and contains only
           lowercase, numbers and _
        '''
        self.check_result('C0001', '#/types/foo1_', Result.PASSED,
                          'types:\n'
                          '  foo1_: { type: string }')

        self.check_result('C0001', '#/types/1foo', Result.FAILED,
                          'types:\n'
                          '  1foo: { type: string }')

        self.check_result('C0001', '#/types/Foo', Result.FAILED,
                          'types:\n'
                          '  Foo: { type: string }')

        self.check_result('C0001', '#/types/foo!', Result.FAILED,
                          'types:\n'
                          '  foo!: { type: string }')

    def test_rule_C0002(self):
        """ Type should not end in _type """

        self.check_result('C0002', '#/types/foo', Result.PASSED,
                          'types:\n'
                          '  foo: { type: string }')

        self.check_result('C0002', '#/types/foo_type', Result.FAILED,
                          'types:\n'
                          '  foo_type: { type: string }')

    def test_rule_C0003(self):
        """ Resource should not end in _resource """

        self.check_result('C0003', '#/resources/foo', Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }')

        self.check_result('C0003', '#/resources/foo_resource', Result.FAILED,
                          'resources:\n'
                          '  foo_resource:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }')

    def test_rule_C0004(self):
        ''' The name of a link should not start or end with ``link``'''

        self.check_result('C0004', '#/resources/foo/links/bar',
                          Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      bar:\n'
                          '        path: /foo/yep\n'
                          '        method: GET')

        self.check_result('C0004', '#/resources/foo/links/foo_link',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '      foo_link:\n'
                          '        path: /foo/nope\n'
                          '        method: GET')

    def test_rule_C0005(self):
        ''' A resource, type, link, or relation name must be
            at least 2 characters long
        '''

        self.check_result('C0005', '#/types/a_good_type_name',
                          Result.PASSED,
                          'types:\n'
                          '  a_good_type_name:\n'
                          '    type: object\n')

        self.check_result('C0005', '#/types/t',
                          Result.FAILED,
                          'types:\n'
                          '  t: \n'
                          '    type: object\n')

        self.check_result('C0005', '#/resources/a_good_resource_name',
                          Result.PASSED,
                          'resources:\n'
                          '  a_good_resource_name:\n'
                          '    type: object\n')

        self.check_result('C0005', '#/resources/r',
                          Result.FAILED,
                          'resources:\n'
                          '  r:\n'
                          '    type: object\n')

        self.check_result('C0005', '#/resources/res/links/a_good_link_name',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self: { path: /res }\n'
                          '      a_good_link_name:\n'
                          '        method: GET\n')

        self.check_result('C0005', '#/resources/res/links/l',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self: { path: /res }\n'
                          '      l:\n'
                          '        method: GET\n')

    def test_rule_C0006(self):
        ''' The service definition must have a valid description field,
            starting with a capital letter
        '''

        self.check_result('C0006',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'description: Test description')

        self.check_result('C0006',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'description: test description')

        self.check_result('C0006',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'description: ')

        self.check_result('C0006', 'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test\n')

    def test_rule_E0002(self):
        ''' Required fields should exist in properties if
            additionalProperties is False
        '''
        self.check_result('E0002', '#/types/foo', Result.PASSED,
                          'types:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      name: { type: string }\n'
                          '    required: [ name ]\n'
                          '    additionalProperties: false')

        self.check_result('E0002', '#/types/foo', Result.FAILED,
                          'types:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      name: { type: string }\n'
                          '    required: [ nonesuch ]\n'
                          '    additionalProperties: false')

        self.check_result('E0002', '#/types/foo', Result.PASSED,
                          'types:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      name: { type: string }\n'
                          '    required: [ nonesuch ]\n'
                          '    additionalProperties: true')

        self.check_result('E0002', '#/resources/foo', Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '    required: [id]\n'
                          '    additionalProperties: false')

        self.check_result('E0002', '#/resources/foo', Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '    required: [id, non_existing_prop]\n'
                          '    additionalProperties: False')

        # check the recursive
        self.check_result('E0002', '#/resources/foo', Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: object\n'
                          '        properties:\n'
                          '          inner: { type: number } \n'
                          '        required: [inner]\n'
                          '        additionalProperties: False\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')

        self.check_result('E0002', '#/resources/foo/properties/outer',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: object\n'
                          '        properties:\n'
                          '          inner: { type: number } \n'
                          '        required: [inner, non_present]\n'
                          '        additionalProperties: False\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')

        self.check_result('E0002', '#/resources/foo/properties/outer/items',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: array\n'
                          '        items:\n'
                          '           type: object\n'
                          '           properties:\n'
                          '              inner: { type: number } \n'
                          '           required: [inner, non_present]\n'
                          '           additionalProperties: False\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')

    def test_rule_E0003(self):
        '''relations should be valid. The specified resource must be found'''

        self.check_result('E0003', '#/resources/info/relations/foo',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    relations:\n'
                          '      foo:\n'
                          '        resource: \'#/resources/info\'\n')

        self.check_result('E0003', '#/resources/info/relations/foo',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    relations:\n'
                          '      foo:\n'
                          '        resource: \'#/resources/foo\'\n')

        # when relations is nested inside of each element of an array
        self.check_result('E0003', '#/resources/info/items/relations/foo',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: array\n'
                          '    items:\n'
                          '      relations:\n'
                          '        foo:\n'
                          '          resource: \'#/resources/info\'\n')

        self.check_result('E0003', '#/resources/info/items/relations/foo',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: array\n'
                          '    items:\n'
                          '      relations:\n'
                          '        foo:\n'
                          '          resource: \'#/resources/foo\'\n')

    def test_rule_C0100(self):
        '''  Standard links must not have a description field. '''

        self.check_result('C0100', '#/resources/res/links/self',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n')

        self.check_result('C0100', '#/resources/res/links/self',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '        description: needless description\n')

    def test_rule_C0101(self):
        ''' A non-standard link must have a valid description field. '''

        self.check_result('C0101', '#/resources/res/links/buy',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      buy:\n'
                          '        method: GET\n'
                          '        path: "/path"\n'
                          '        description: non capital description\n')

        self.check_result('C0101', '#/resources/res/links/buy',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      buy:\n'
                          '        method: GET\n'
                          '        path: "/path"\n'
                          '        description: buy it\n')

        self.check_result('C0101', '#/resources/res/links/buy',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      buy:\n'
                          '        method: GET\n'
                          '        path: "/path"\n'
                          '        description: Capital description\n')

    def test_rule_W0100(self):
        '''  A ``get`` link cannot have a request body '''

        self.check_result('W0100', '#/resources/res/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: GET\n'
                          '        request: { type: string }\n')

        self.check_result('W0100', '#/resources/res/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: GET\n')

    def test_rule_W0101(self):
        '''  A ``get`` link cannot have a request body '''

        self.check_result('W0101', '#/resources/res/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: GET\n'
                          '        response: { type: string }\n')

        self.check_result('W0101', '#/resources/res/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: GET\n'
                          '        response: { $ref: "#/resources/res" }\n')

    def test_rule_W0102(self):
        '''A ``set`` link request must be the representation
           of the resource it belongs to
        '''

        self.check_result('W0102', '#/resources/res/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n'
                          '        request: { $ref: "#/resources/res" }\n')

        self.check_result('W0102', '#/resources/res/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n'
                          '        request: { type: string }\n')

    def test_rule_W0103(self):
        '''A ``set`` link response must be null or the representation
          of the resource it belongs to
        '''

        self.check_result('W0103', '#/resources/res/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n')

        self.check_result('W0103', '#/resources/res/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n'
                          '        response: { type: string }\n')

        self.check_result('W0103', '#/resources/res/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n'
                          '        response: { $ref: "#/resources/res" }\n')

    def test_rule_W0104(self):
        ''' A ``delete`` link cannot have a request body '''

        self.check_result('W0104', '#/resources/res/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: DELETE\n'
                          '        request: { type: string }\n')

        self.check_result('W0104', '#/resources/res/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: DELETE\n')

    def test_rule_W0105(self):
        ''' A ``delete`` link cannot have a response body '''

        self.check_result('W0105', '#/resources/res/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: DELETE\n'
                          '        response: { type: string }\n')

        self.check_result('W0105', '#/resources/res/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: DELETE\n')

    def test_rule_W0106(self):
        '''A ``create`` link must have a request body '''

        self.check_result('W0106', '#/resources/res/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n')

        self.check_result('W0106', '#/resources/res/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n'
                          '        request: { type: string }\n')

    def test_rule_W0107(self):
        ''' A ``create`` link request must not be the same
            as the resource it belongs to
        '''

        self.check_result('W0107', '#/resources/res/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n'
                          '        request: { $ref: "#/resources/res"}\n')

        self.check_result('W0107', '#/resources/res/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n'
                          '        request: { type: string }\n')

    def test_rule_W0108(self):
        '''A ``create`` link response must not be the same as
           the resource it belongs to
        '''

        self.check_result('W0108', '#/resources/res/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n'
                          '        response: { $ref: "#/resources/res"}\n')

        self.check_result('W0108', '#/resources/res/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n'
                          '        response: { type: string }\n')

    def test_rule_W0112(self):
        ''' A link should not end with / '''

        self.check_result('W0112', '#/resources/foo/links/self',
                          Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/foo"\n'
                          '      bar:\n'
                          '        method: POST\n'
                          '        path: /foo/bar\n')

        # Self link
        self.check_result('W0112', '#/resources/foo/links/self',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/foo/"\n'
                          '      bar:\n'
                          '        method: POST\n'
                          '        path: /foo/bar\n')

        # Bar link with inherited path
        self.check_result('W0112', '#/resources/foo/links/bar',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/foo/"\n'
                          '      bar:\n'
                          '        method: POST\n')

        # Bar link with explicit path
        self.check_result('W0112', '#/resources/foo/links/bar',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/foo"\n'
                          '      bar:\n'
                          '        method: POST\n'
                          '        path: /foo/bar/\n')

        # Special check for root
        self.check_result('W0112', '#/resources/foo/links/self',
                          Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: string\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/"\n')

    def test_rule_E0100(self):
        ''' A ``get`` link must use http method GET '''

        self.check_result('E0100', '#/resources/res/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: GET\n')

        self.check_result('E0100', '#/resources/res/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      get:\n'
                          '        method: PUT\n')

    def test_rule_E0101(self):
        '''  A ``set`` link must use http method PUT '''

        self.check_result('E0101', '#/resources/res/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: PUT\n')

        self.check_result('E0101', '#/resources/res/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      set:\n'
                          '        method: GET\n')

    def test_rule_E0102(self):
        '''  A ``create`` link must use http method POST '''

        self.check_result('E0102', '#/resources/res/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: POST\n')

        self.check_result('E0102', '#/resources/res/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      create:\n'
                          '        method: GET\n')

    def test_rule_E0103(self):
        '''  A ``delete`` link must use http method DELETE '''

        self.check_result('E0103', '#/resources/res/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: DELETE\n')

        self.check_result('E0103', '#/resources/res/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self:\n'
                          '        path: "/path"\n'
                          '      delete:\n'
                          '        method: GET\n')

    def test_rule_E0105(self):
        '''A parameter in URI template must be declared in schema properties'''

        self.check_result('E0105', '#/resources/foo/links/self', Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '    links:\n'
                          '      self: { path: "/foos/{id}" }\n')
        self.check_result('E0105', '#/resources/foo/links/self', Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '    links:\n'
                          '      self: { path: "/foos/{non_present}" }\n')
        self.check_result('E0105', '#/resources/foo/links/self', Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: "null"\n'
                          '    links:\n'
                          '      self: { path: "/foos/{non_present}" }\n')

    def test_rule_C0303(self):
        ''' Self link should be the first link '''

        self.check_result('C0303', '#/resources/r1', Result.PASSED,
                          'resources:\n'
                          '  r1:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self: { path: "/r1" }\n')

        self.check_result('C0303', '#/resources/r4', Result.PASSED,
                          'resources:\n'
                          '  r4:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      r4_l1: { method: GET, path: "/r4" }\n')

        self.check_result('C0303', '#/resources/r2', Result.FAILED,
                          'resources:\n'
                          '  r2:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      r2_l1: { method: GET, path: "/dsaf" }\n'
                          '      r2_l2: { method: GET, path: "/dsaf" }\n'
                          '      r2_l3: { method: GET, path: "/dsaf" }\n'
                          '      self: { path: "/r2" }\n')

        self.check_result('C0303', '#/resources/r3', Result.PASSED,
                          'resources:\n'
                          '  r3:\n'
                          '    type: object\n'
                          '    links:\n'
                          '      self: { path: "/r3" }\n'
                          '      r3_l1: { method: GET, path: "/dsaf" }\n'
                          '      r3_l2: { method: GET, path: "/dsaf" }\n'
                          '      r3_l3: { method: GET, path: "/dsaf" }\n')

    def test_rule_C0200(self):
        ''' A type must have a valid description field '''

        self.check_result('C0200', '#/types/a_type', Result.PASSED,
                          'types:\n'
                          '  a_type:\n'
                          '    type: object\n'
                          '    description: A good description\n')

        self.check_result('C0200', '#/types/a_type', Result.FAILED,
                          'types:\n'
                          '  a_type:\n'
                          '    type: object\n'
                          '    description: a bad description\n')

    def test_rule_C0300(self):
        ''' A resource must have a valid description field '''

        self.check_result('C0300', '#/resources/res', Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    description: A good description\n')

        self.check_result('C0300', '#/resources/res', Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n'
                          '    description: a bad description\n')

    def test_rule_C0301(self):
        '''  A resource should be an object '''

        self.check_result('C0301', '#/resources/res', Result.PASSED,
                          'resources:\n'
                          '  res:\n'
                          '    type: object\n')

        self.check_result('C0301', '#/resources/res', Result.FAILED,
                          'resources:\n'
                          '  res:\n'
                          '    type: string\n')

    def test_rule_W0006(self):
        """ A required property should not have a default value """
        self.check_result('W0006', '#/resources/foo', Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '    required: [id]')
        self.check_result('W0006', '#/resources/foo', Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number, default: 0 }\n'
                          '    links:\n'
                          '      self: { path: /foo }\n'
                          '    required: [id]')
        # check the recursive
        self.check_result('W0006', '#/resources/foo/properties/outer',
                          Result.PASSED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: object\n'
                          '        properties:\n'
                          '          inner: { type: number }\n'
                          '        required: [inner]\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')

        self.check_result('W0006', '#/resources/foo/properties/outer',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: object\n'
                          '        properties:\n'
                          '          inner: { type: number, default: 0 }\n'
                          '        required: [inner]\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')

        self.check_result('W0006', '#/resources/foo/properties/outer/items',
                          Result.FAILED,
                          'resources:\n'
                          '  foo:\n'
                          '    type: object\n'
                          '    properties:\n'
                          '      id: { type: number }\n'
                          '      outer:\n'
                          '        type: array\n'
                          '        items:\n'
                          '           type: object\n'
                          '           properties:\n'
                          '              inner: {type: number,default: 0}\n'
                          '           required: [inner]\n'
                          '    links:\n'
                          '      self: { path: /foo }\n')


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
