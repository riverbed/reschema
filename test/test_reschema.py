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

    def test_unknown_schema(self):
        import tempfile
        fd, name = tempfile.mkstemp(suffix='.txt', text=True)

        try:
            f = os.fdopen(fd, 'w')
            f.write('testingdata')
            f.close()

            r = reschema.RestSchema()
            with self.assertRaises(ValueError):
                r.load(name)
        finally:
            os.unlink(name)

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
        resources = [x for x in r.resource_iter()]
        self.assertEqual(len(resources), 8)


    def test_find_name_basic(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        a = r.find('author')
        self.assertEqual(a.id, 'author')
        with self.assertRaises(KeyError):
            r.find('no_type')

    def test_find_name_complex(self):
        r = reschema.RestSchema()
        r.load(TEST_SCHEMA_YAML)
        c = r.find('/book/chapters')
        self.assertEqual(c.id, 'chapters')
        self.assertEqual(c._type, 'array')
        self.assertEqual(c.typestr, 'array of <object>')
        c = r.find('/book/chapters/1')
        self.assertEqual(c.fullid(), '/book/chapters/items')
        self.assertEqual(c._type, 'object')
        c = r.find('/book/author_ids')
        self.assertEqual(c._type, 'array')
        c = r.find('/book/author_ids/1')
        self.assertEqual(c._type, 'number')

        with self.assertRaises(KeyError):
            r.find('no_type')

class TestCatalog(unittest.TestCase):

    def setUp(self):
        self.r = reschema.RestSchema()
        self.r.load(TEST_SCHEMA_YAML)

    def tearDown(self):
        self.r = None

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
        self.assertIsInstance(repr(s), str)

    def test_object_xml(self):
        book = self.r.find('book')
        p = {'id': 1,
             'title': '50 Shades of JSON',
             'publisher_id': 2,
             'author_ids': [50, 51],
             'chapters': [{'num': 1, 'heading': 'Chapter 1'},
                          {'num': 2, 'heading': 'Chapter 2'},
                          {'num': 3, 'heading': 'Chapter 3'},
                          ]}
        self.assertIsNone(book.validate(p))
        xml = book.toxml(p)
        self.assertEqual(xml.attrib['id'], '1')

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
        self.assertEqual(len(book.str_simple().split()), 47)
        self.assertEqual(len(book.str_detailed().split()), 18)
        self.assertEqual(book['links'], book.links)

        a = book['author_ids']
        self.assertEqual(type(a), Array)
        self.assertEqual(book['/author_ids'], a)

        # Test JSON pointer syntax
        self.assertEqual(type(book['author_ids'][0]), Number)
        self.assertEqual(book['/author_ids/0'], book['author_ids'][0])

        # Test relative JSON pointer syntax
        a0 = book['/author_ids/0']
        self.assertEqual(a0['/'], a0)
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

    def check_valid(self, s, valid=None, invalid=None, toxml=False):
        schema = self.parse(s)
        for a in valid:
            schema.validate(a)
            if toxml:
                schema.toxml(a)

        for a in invalid:
            with self.assertRaises(ValidationError):
                schema.validate(a)

    def check_bad_schema(self, s, etype):
        with self.assertRaises(etype):
            self.parse(s)

    def test_missing_api(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        with self.assertRaises(ParseError):
            Schema.parse(d)

    def test_unnamed(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        j = Schema.parse(d, api='/')
        self.assertTrue(j.name.startswith('element'))

    def test_unknown_type(self):
        s = "type: foobrobicator\n"
        d = yaml_loader.marked_load(s)
        with self.assertRaises(ParseError):
            Schema.parse(d, api='/')

    def test_boolean(self):
        self.check_valid("type: boolean\n",

                         # values to validate
                         valid=[True,
                                False],

                         invalid=["TRUE",
                                  "FALSE",
                                  "1",
                                  1]
                         )

    def test_ref(self):
        # missing ref
        # XXX needs work
        self.check_bad_schema("publishers:\n"
                              "     type: array\n"
                              "     items: { $ref: publisher }\n",
                              ParseError)

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
                         valid=["aa",
                                "11",
                                "abc",
                                "123",
                                "1234512345"],

                         invalid=["A",
                                  "abcABCD",
                                  "12345123451"]
                         )

        self.check_valid("type: string\n"
                         "enum: [one, two, three]\n",

                         # values to validate
                         valid=["one",
                                "two",
                                "three"],

                         invalid=["four",
                                  "one1",
                                  "onetwo"]
                         )

    def test_object_simple(self):
        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n",

                         # values to validate
                         valid=[{"foo": 1,
                                 "bar": "one"}],
                         
                         invalid=[{"foo": 1,
                                   "baz": "one"},
                                  'not a dict'],
                         toxml=True
                         )

    def test_object_add_props_simple(self):
        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n"
                         "additionalProperties: true",

                         # values to validate
                         valid=[{"foo": 1,
                                 "bar": "one",
                                 "baz": 2}],
                         
                         invalid=[{"foo": "one",
                                   "baz": "one"}]
                         )

    def test_object_add_props_complex(self):
        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n"
                         "additionalProperties: { type: number }\n",

                         # values to validate
                         valid=[{"foo": 1,
                                 "bar": "one",
                                 "baz": 2}],

                         invalid=[{"foo": 1,
                                   "bar": "one",
                                   "baz": "two"}],
                         toxml=True
                         )


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
