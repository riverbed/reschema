# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.
from __future__ import print_function

import os
import logging
import unittest
import yaml

import reschema
from reschema.lint import Validator, Result

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yml')

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

    data = yaml.load(fragment)

    template = yaml.load(SERVICE_DEF_TEMPLATE)
    template.update(data)

    sdef = reschema.ServiceDef.create_from_text(yaml.dump(template),
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
        ''' the provider field must be set to riverbed'''
        self.check_result('W0001', 'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'provider: riverbed\n'
                          'name: test\n')

        self.check_result('W0001', 'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'provider: test\n'
                          'name: test\n')

    def test_rule_W0002(self):
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
        '''the schema must have a title'''
        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test\n'
                          'title: one_title')

        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test\n')

        self.check_result('W0004',
                          'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'

                          'name: test\n')

    def test_rule_C0001(self):
        """name should start with a letter and contains only
           lowercase, numbers and _
        """
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
        """ Link should not end in _link """

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
        """ name must be at least 2 characters long """

        self.check_result('C0005', '#/types/foo', Result.PASSED,
                          'types:\n'
                          '  foo: { type: string }')

        self.check_result('C0005', '#/types/f', Result.FAILED,
                          'types:\n'
                          '  f: { type: string }')

    def test_rule_C0006(self):
        """ ServiceDef must have a valid description field
            starting with a capitalized letter
        """
        self.check_result('C0006', 'http://support.riverbed.com/apis/test/1.0',
                          Result.PASSED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'description: Test\n'
                          'name: test\n')

        self.check_result('C0006', 'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'description: test\n'
                          'name: test\n')

        self.check_result('C0006', 'http://support.riverbed.com/apis/test/1.0',
                          Result.FAILED,
                          'id: http://support.riverbed.com/apis/test/1.0\n'
                          'name: test\n')

    def test_rule_E0002(self):
        """ Required fields should exist in properties if
        additionalProperties is False"""
        # import pdb;pdb.set_trace()
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

    def test_rule_C0100(self):
        '''standard links must not have description field'''
        self.check_result('C0100', '#/resources/info/links/self',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        self: { path: "$/path" }\n')

        self.check_result('C0100', '#/resources/info/links/self',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        self:\n'
                          '            path: "$/test_descr"\n'
                          '            description: "self link"\n')

    def test_rule_C0101(self):
        '''non-standard links must have description field'''
        self.check_result('C0101', '#/resources/info/links/l1',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        l1:\n'
                          '            path: "$/l1"\n'
                          '            description: "Desc"\n'
                          '            method: POST\n')

        self.check_result('C0101', '#/resources/info/links/l1',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        l1:\n'
                          '            path: "$/l1"\n'
                          '            method: POST\n')

    def test_rule_W0100(self):
        '''a get link cannot have a request body'''
        self.check_result('W0100', '#/resources/info/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/l1"\n'
                          '            method: GET\n')

        self.check_result('W0100', '#/resources/info/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/l1"\n'
                          '            method: GET\n'
                          '            request: '
                          '{ $ref: "#/resources/info" }\n')

    def test_rule_W0101(self):
        '''a get link response must represent the resource it belongs'''
        self.check_result('W0101', '#/resources/info/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/get"\n'
                          '            method: GET\n'
                          '            response: { $ref: "#/resources/info" }')

        self.check_result('W0101', '#/resources/info/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  info1: { type: string }\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/get"\n'
                          '            method: GET\n'
                          '            response:\n'
                          '                $ref: "#/resources/info1"\n')

    def test_rule_W0102(self):
        '''a set link request must represent the resource it belongs'''
        self.check_result('W0102', '#/resources/info/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n'
                          '            request: { $ref: "#/resources/info" }')

        self.check_result('W0102', '#/resources/info/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  info1: { type: string }\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n'
                          '            request: \n'
                          '                $ref: "#/resources/info1"\n')

    def test_rule_W0103(self):
        '''A set link response must be null or the representation of
           the resource it belongs
        '''
        self.check_result('W0103', '#/resources/info/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n'
                          '            response: { $ref: "#/resources/info" }')

        self.check_result('W0103', '#/resources/info/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n'
                          '            response: null')

        self.check_result('W0103', '#/resources/info/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  info1: { type: string }\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n'
                          '            response:\n'
                          '                $ref: "#/resources/info1"\n')

    def test_rule_W0104(self):
        '''A delete link cannot have a request body'''

        self.check_result('W0104', '#/resources/info/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: DELETE\n')

        self.check_result('W0104', '#/resources/info/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: DELETE\n'
                          '            request: { $ref: "#/resources/info" }')

    def test_rule_W0105(self):
        '''A delete link cannot have a response body'''

        self.check_result('W0105', '#/resources/info/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: DELETE\n')

        self.check_result('W0105', '#/resources/info/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: DELETE\n'
                          '            response: { $ref: "#/resources/info" }')

    def test_rule_W0106(self):
        '''A create link must have a request body'''

        self.check_result('W0106', '#/resources/info/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n'
                          '            request: { $ref: "#/resources/info" }')

        self.check_result('W0106', '#/resources/info/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n')

    def test_rule_W0107(self):
        '''A create link request must not be the same as the
           resource it belongs
        '''

        self.check_result('W0107', '#/resources/info/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  info1: { type: string }\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n'
                          '            request: { $ref: "#/resources/info1" }')

        self.check_result('W0107', '#/resources/info/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n'
                          '            request: { $ref: "#/resources/info" }')

    def test_rule_W0108(self):
        '''A create link response must not be the same as the
           resource it belongs
        '''

        self.check_result('W0108', '#/resources/info/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  info1: { type: string }\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n'
                          '            response:\n'
                          '                $ref: "#/resources/info1"\n')

        self.check_result('W0108', '#/resources/info/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n'
                          '            response: { $ref: "#/resources/info" }')

    def test_rule_E0100(self):
        '''A get link must use http method GET'''

        self.check_result('E0100', '#/resources/info/links/get',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/get"\n'
                          '            method: GET\n')

        self.check_result('E0100', '#/resources/info/links/get',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        get:\n'
                          '            path: "$/resources/info/links/get"\n'
                          '            method: PUT\n')

    def test_rule_E0101(self):
        '''A set link must use http method PUT'''

        self.check_result('E0101', '#/resources/info/links/set',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: PUT\n')

        self.check_result('E0101', '#/resources/info/links/set',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        set:\n'
                          '            path: "$/resources/info/links/set"\n'
                          '            method: GET\n')

    def test_rule_E0102(self):
        '''A create link must use http method POST'''

        self.check_result('E0102', '#/resources/info/links/create',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: POST\n')

        self.check_result('E0102', '#/resources/info/links/create',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        create:\n'
                          '            path: "$/resources/info/links/create"\n'
                          '            method: PUT\n')

    def test_rule_E0103(self):
        '''A delete link must use http method DELETE'''

        self.check_result('E0103', '#/resources/info/links/delete',
                          Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: DELETE\n')

        self.check_result('E0103', '#/resources/info/links/delete',
                          Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: object\n'
                          '    links:\n'
                          '        delete:\n'
                          '            path: "$/resources/info/links/delete"\n'
                          '            method: PUT\n')

    def test_rule_C0200(self):
        """ type must have a valid description
        """
        self.check_result('C0200', '#/types/name',
                          Result.PASSED,
                          'types:\n'
                          '  name:\n'
                          '      type: string\n'
                          '      description: Desc')

        self.check_result('C0200', '#/types/name',
                          Result.FAILED,
                          'types:\n'
                          '  name:\n'
                          '      type: string\n'
                          '      description: desc')

        self.check_result('C0200', '#/types/name',
                          Result.FAILED,
                          'types:\n'
                          '  name:\n'
                          '      type: string\n')

    def test_rule_C0300(self):
        """ resource must have a valid description
        """
        self.check_result('C0300', '#/resources/name',
                          Result.PASSED,
                          'resources:\n'
                          '  name:\n'
                          '      type: string\n'
                          '      description: Desc')

        self.check_result('C0300', '#/resources/name',
                          Result.FAILED,
                          'resources:\n'
                          '  name:\n'
                          '      type: string\n'
                          '      description: desc')

        self.check_result('C0300', '#/resources/name',
                          Result.FAILED,
                          'resources:\n'
                          '  name:\n'
                          '      type: string\n')

    def test_rule_C0301(self):
        """ resource should be an object
        """
        self.check_result('C0301', '#/resources/name',
                          Result.PASSED,
                          'resources:\n'
                          '  name:\n'
                          '      type: object')

        self.check_result('C0301', '#/resources/name',
                          Result.FAILED,
                          'resources:\n'
                          '  name:\n'
                          '      type: string')

if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
