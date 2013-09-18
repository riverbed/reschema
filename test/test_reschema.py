# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import logging
import unittest

from yaml.error import MarkedYAMLError

import reschema
from reschema.jsonschema import ValidationError, ParseError
from reschema.jsonschema import Object, Number, String, Array, Schema
from reschema import yaml_loader

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
PACKAGE_PATH = os.path.dirname(TEST_PATH)
TEST_SCHEMA_DIR = os.path.join(PACKAGE_PATH, 'examples')

TEST_SCHEMA_YAML = os.path.join(TEST_SCHEMA_DIR, 'Catalog.yml')
TEST_SCHEMA_JSON = os.path.join(TEST_SCHEMA_DIR, 'Catalog.json')


class TestReschema(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_schema(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        self.assertEqual(r.name, 'Catalog')

    def test_load_schema_json(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_JSON)
        self.assertEqual(r.name, 'Catalog')

    def test_parse_schema(self):
        r = reschema.RestSchema()
        with open(TEST_SCHEMA_YAML, 'r') as f:
            r.parse_text(f.read(), format='yaml')
        self.assertEqual(r.name, 'Catalog')

    def test_parse_schema_json(self):
        r = reschema.RestSchema()
        with open(TEST_SCHEMA_JSON, 'r') as f:
            r.parse_text(f.read())
        self.assertEqual(r.name, 'Catalog')

    def test_load_bad_schema(self):
        with open(TEST_SCHEMA_YAML, 'r') as f:
            schema = f.readlines()
        schema.insert(31, '      bad_object_name: foo\n')

        r = reschema.RestSchema()
        with self.assertRaises(MarkedYAMLError):
            r.parse_text(''.join(schema), format='yml')

    def test_resource_load(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        self.assertEquals(len(r.resources), 8)
        self.assertIn('info', r.resources)
        self.assertIn('author', r.resources)
        self.assertIn('authors', r.resources)
        self.assertTrue(r.find_resource('author'))
        with self.assertRaises(KeyError):
            r.find_resource('no_resource')

    def test_type_load(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        self.assertIn('address', r.types)
        self.assertTrue(r.find_type('address'))
        with self.assertRaises(KeyError):
            r.find_type('no_type')

    def test_resource_objects(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        a = r.resources['author']
        self.assertFalse(a.isRef())
        self.assertFalse(a.isSimple())
        self.assertIn('id', a.props)
        self.assertIn('name', a.props)
        self.assertEqual(a.id, 'author')
        self.assertIsNone(a.parent)


class TestCatalog(unittest.TestCase):

    def setUp(self):
        self.r = reschema.RestSchema()
        self.r.load(TEST_SCHEMA_YAML)

    def tearDown(self):
        self.r = None

    def test_boolean(self):
        # TODO add Boolean type to Catalog.yml
        pass

    def test_string(self):
        s = self.r.resources['author'].props['name']
        self.assertFalse(s.isRef())
        self.assertTrue(s.isSimple())

        # successful validation will return None
        self.assertIsNone(s.validate('foo'))
        self.assertIsNone(s.validate(u'bar'))

        with self.assertRaises(ValidationError):
            s.validate(42)

    def test_number(self):
        n = self.r.resources['author'].props['id']
        self.assertFalse(n.isRef())
        self.assertTrue(n.isSimple())

        # successful validation will return None
        self.assertIsNone(n.validate(443))
        self.assertIsNone(n.validate(3.14))

        with self.assertRaises(ValidationError):
            n.validate('foo')
        with self.assertRaises(ValidationError):
            n.validate('43')

    def test_timestamp(self):
        pass

    def test_timestamp_hp(self):
        pass

    def test_object(self):
        # skip validation, we are checking that elsewhere
        s = self.r.resources['author']
        self.assertFalse(s.isRef())
        self.assertFalse(s.isSimple())

    def test_array(self):
        s = self.r.resources['authors']
        self.assertFalse(s.isRef())
        self.assertFalse(s.isSimple())

        # successful validation will return None
        self.assertIsNone(s.validate([{'id': 1, 'name': 'Ted Nugent'},
                                      {'id': 2, 'name': 'Ralph Macchio'}]))

        with self.assertRaises(ValidationError):
            s.validate('foo')

    def test_indexing(self):
        book = self.r.resources['book']
        self.assertEqual(type(book), Object)
        self.assertEqual(type(book['id']), Number)
        self.assertEqual(type(book['title']), String)

        a = book['author_ids']
        self.assertEqual(type(a), Array)
        self.assertEqual(book['/author_ids'], a)

        # Test JSON pointer syntax
        self.assertEqual(type(book['author_ids'][0]), Number)
        self.assertEqual(book['/author_ids/0'], book['author_ids'][0])

        # Test relative JSON pointer syntax
        a0 = book['/author_ids/0']
        self.assertEqual(a0['2/'], book)
        self.assertEqual(a0['2/id'], book['id'])

        with self.assertRaises(KeyError): book['foo']
        with self.assertRaises(KeyError): book['1/']
        with self.assertRaises(KeyError): a['a']
        with self.assertRaises(KeyError): a['10a']
        with self.assertRaises(KeyError): a0['3/']


class TestJsonSchema(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def parse(self, string):
        d = yaml_loader.marked_load(string)
        return Schema.parse(d, 'root', api='/api')

    def check_valid(self, s, valid=[], invalid=[]):
        schema = self.parse(s)
        for a in valid:
            schema.validate(a)

        for a in invalid:
            try:
                schema.validate(a)
                self.fail("ValidationError not raised for value: %s" % a)
            except ValidationError:
                pass

    def check_bad_schema(self, s, etype):
        try:
            self.parse(s)
        except etype, e:
            logger.debug("Got validation error: %s" % str(e))
            return

        self.fail('Schema should have thrown a ValidationError')

    def test_string(self):
        self.check_bad_schema("type: string\n"
                              "foobar: bad property",
                              ParseError)

        self.check_bad_schema("type: string\n"
                              "minLength: 2a",
                              ParseError)

        self.check_valid("type: string\n"
                         "minLength: 2\n"
                         "maxLength: 10\n"
                         "pattern: '[a-z0-9]+'\n",

                         # values to validate
                         valid = [ "aa",
                                   "11",
                                   "abc",
                                   "123",
                                   "1234512345" ],

                         invalid = [ "A",
                                     "abcABCD",
                                     "12345123451" ]
                         )

        self.check_valid("type: string\n"
                         "enum: [one, two, three]\n",

                         # values to validate
                         valid = [ "one",
                                   "two",
                                   "three" ],

                         invalid = [ "four",
                                     "one1",
                                     "onetwo" ]
                         )

    def test_object(self):
        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n",

                         # values to validate
                         valid = [ { "foo" : 1, "bar" : "one" } ],
                         
                         invalid = [ { "foo" : 1, "baz" : "one" } ])

        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n"
                         "additionalProperties: true", 

                         # values to validate
                         valid = [ { "foo" : 1, "bar" : "one", "baz": 2} ],
                         
                         invalid = [ { "foo" : "one", "baz" : "one" } ])

        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n"
                         "additionalProperties: { type: number }\n", 

                         # values to validate
                         valid = [ { "foo" : 1, "bar" : "one", "baz": 2} ],

                         invalid = [ { "foo" : 1, "bar" : "one", "baz": "two"} ])


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
