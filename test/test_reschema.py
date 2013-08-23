# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import logging
import unittest

import reschema

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
PACKAGE_PATH = os.path.dirname(TEST_PATH)
TEST_SCHEMA_DIR = os.path.join(PACKAGE_PATH, 'examples')
TEST_SCHEMA = os.path.join(TEST_SCHEMA_DIR, 'Catalog.yml')


class ReschemaTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_schema(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA)
        self.assertEqual(r.name, 'Catalog')

    def test_resource_load(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA)
        self.assertEquals(len(r.resources), 8)
        self.assertIn('info', r.resources)
        self.assertIn('author', r.resources)
        self.assertIn('authors', r.resources)
        self.assertTrue(r.find_resource('author'))
        with self.assertRaises(KeyError):
            r.find_resource('no_resource')

    def test_type_load(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA)
        self.assertIn('address', r.types)
        self.assertTrue(r.find_type('address'))
        with self.assertRaises(KeyError):
            r.find_type('no_type')

    def test_resource_objects(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA)
        a = r.resources['author']
        self.assertFalse(a.isRef())
        self.assertFalse(a.isSimple())
        self.assertIn('id', a.props)
        self.assertIn('name', a.props)


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
