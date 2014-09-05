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
title: Test relint
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


class TestRelint(TestLintBase):

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

        self.check_result('E0003', '#/resources/info/relations/foo', Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    relations:\n'
                          '      foo:\n'
                          '        resource: \'#/resources/info\'\n')

        self.check_result('E0003', '#/resources/info/relations/foo', Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    relations:\n'
                          '      foo:\n'
                          '        resource: \'#/resources/foo\'\n')

        # when relations is nested inside of each element of an array
        self.check_result('E0003', '#/resources/info/items/relations/foo', Result.PASSED,
                          'resources:\n'
                          '  info:\n'
                          '    type: array\n'
                          '    items:\n'
                          '      relations:\n'
                          '        foo:\n'
                          '          resource: \'#/resources/info\'\n')

        self.check_result('E0003', '#/resources/info/items/relations/foo', Result.FAILED,
                          'resources:\n'
                          '  info:\n'
                          '    type: array\n'
                          '    items:\n'
                          '      relations:\n'
                          '        foo:\n'
                          '          resource: \'#/resources/foo\'\n')

if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
