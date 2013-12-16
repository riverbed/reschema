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
from reschema.exceptions import ValidationError, ParseError, MissingParameter
from reschema.jsonschema import Object, Integer, Number, String, Array, Schema
from reschema import yaml_loader

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_SCHEMA_YAML = os.path.join(TEST_PATH, 'test_schema.yml')

PACKAGE_PATH = os.path.dirname(TEST_PATH)

EXAMPLES_DIR = os.path.join(PACKAGE_PATH, 'examples')
CATALOG_YAML = os.path.join(EXAMPLES_DIR, 'Catalog.yml')
CATALOG_JSON = os.path.join(EXAMPLES_DIR, 'Catalog.json')


class TestReschema(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_schema(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
        self.assertEqual(r.name, 'catalog')

    def test_load_schema_json(self):
        r = reschema.RestSchema()
        r.load(CATALOG_JSON)
        self.assertEqual(r.name, 'catalog')

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
        with open(CATALOG_YAML, 'r') as f:
            r.parse_text(f.read(), format='yaml')
        self.assertEqual(r.name, 'catalog')

    def test_parse_schema_json(self):
        r = reschema.RestSchema()
        with open(CATALOG_JSON, 'r') as f:
            r.parse_text(f.read())
        self.assertEqual(r.name, 'catalog')

    def test_load_bad_schema(self):
        with open(CATALOG_YAML, 'r') as f:
            schema = f.readlines()
        schema.insert(31, '      bad_object_name: foo\n')

        r = reschema.RestSchema()
        with self.assertRaises(MarkedYAMLError):
            r.parse_text(''.join(schema), format='yml')

    def test_resource_load(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
        self.assertEquals(len(r.resources), 8)
        self.assertIn('info', r.resources)
        self.assertIn('author', r.resources)
        self.assertIn('authors', r.resources)
        self.assertTrue(r.find_resource('author'))
        with self.assertRaises(KeyError):
            r.find_resource('no_resource')

    def test_type_load(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
        self.assertIn('address', r.types)
        self.assertTrue(r.find_type('address'))
        with self.assertRaises(KeyError):
            r.find_type('no_type')

    def test_resource_objects(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
        a = r.resources['author']
        self.assertFalse(a.is_ref())
        self.assertFalse(a.is_simple())
        self.assertIn('id', a.props)
        self.assertIn('name', a.props)
        self.assertEqual(a.id, 'author')
        self.assertIsNone(a.parent)
        resources = [x for x in r.resource_iter()]
        self.assertEqual(len(resources), 8)

    def test_find_name_basic(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
        a = r.find('author')
        self.assertEqual(a.id, 'author')
        with self.assertRaises(KeyError):
            r.find('no_type')

    def test_find_name_complex(self):
        r = reschema.RestSchema()
        r.load(CATALOG_YAML)
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
        self.assertEqual(c._type, 'integer')

        with self.assertRaises(KeyError):
            r.find('no_type')


class TestCatalog(unittest.TestCase):

    def setUp(self):
        self.r = reschema.RestSchema()
        self.r.load(CATALOG_YAML)

    def tearDown(self):
        self.r = None

    def test_string(self):
        s = self.r.resources['author'].props['name']
        self.assertFalse(s.is_ref())
        self.assertTrue(s.is_simple())

        # successful validation will return None
        self.assertIsNone(s.validate('foo'))
        self.assertIsNone(s.validate(u'bar'))

        with self.assertRaises(ValidationError):
            s.validate(42)

    def test_integer(self):
        n = self.r.resources['author'].props['id']
        self.assertFalse(n.is_ref())
        self.assertTrue(n.is_simple())

        # successful validation will return None
        self.assertIsNone(n.validate(443))

        with self.assertRaises(ValidationError):
            n.validate('foo')
        with self.assertRaises(ValidationError):
            n.validate('43')
        with self.assertRaises(ValidationError):
            n.validate(3.14)

    def test_reference(self):
        ref = self.r.find('publisher').props['billing_address']
        self.assertFalse(ref.is_simple())
        self.assertTrue(ref.is_ref())
        self.assertEqual(ref.typestr, 'address')

    def test_link_target(self):
        s = self.r.resources['author']
        link = s.relations['instances']
        self.assertEqual(link.resource, self.r.resources['authors'])

    def test_link_path(self):
        pub = self.r.find('publisher')
        link = pub.links['self']
        path = link.path
        self.assertEqual(str(path), '$/publishers/{id}')
        self.assertEqual(path.resolve({'id': 12}), '/api/catalog/1.0/publishers/12')

    def test_link_template_path(self):
        book = self.r.find('book')
        chapters = book.props['chapters']
        items = chapters['items']
        book_chapter = items.relations['full']
        data = {'book': book.example}
        (uri, params) = book_chapter.resolve(data, '/book/chapters/1')
        self.assertEqual(uri, '/api/catalog/1.0/books/100/chapters/2')
        with self.assertRaises(MissingParameter):
            book_chapter.resolve(None)

    def test_object(self):
        # skip validation, we are checking that elsewhere
        s = self.r.resources['author']
        self.assertFalse(s.is_ref())
        self.assertFalse(s.is_simple())
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
        self.assertEqual(sorted(xml.keys()), [u'id', u'publisher_id', u'title'])
        xml_child = book.toxml(p, parent=xml)
        self.assertNotEqual(xml, xml_child)

    def test_array(self):
        s = self.r.resources['authors']
        self.assertFalse(s.is_ref())
        self.assertFalse(s.is_simple())

        # successful validation will return None
        p = [{'id': 1, 'name': 'Ted Nugent'},
             {'id': 2, 'name': 'Ralph Macchio'}]
        self.assertIsNone(s.validate(p))
        xml = s.toxml(p)
        self.assertEqual(len(xml.getchildren()), 2)

        with self.assertRaises(ValidationError):
            s.validate('foo')

    def test_indexing(self):
        book = self.r.resources['book']
        self.assertEqual(type(book), Object)
        self.assertEqual(type(book['id']), Integer)
        self.assertEqual(type(book['title']), String)
        self.assertGreater(len(book.str_simple()), 0)
        self.assertGreater(len(book.str_detailed()), 0)
        self.assertEqual(book['links'], book.links)

        a = book['author_ids']
        self.assertEqual(type(a), Array)
        self.assertEqual(book['/author_ids'], a)

        # Test JSON pointer syntax
        self.assertEqual(type(book['author_ids'][0]), Integer)
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


class TestCatalogLinks(unittest.TestCase):

    def setUp(self):
        self.r = reschema.RestSchema()
        self.r.load(CATALOG_YAML)

    def tearDown(self):
        self.r = None

    def test_links(self):
        book = self.r.resources['book']
        book_data = {'id': 1, 'title': 'My first book', 'publisher_id': 5, 'author_ids' : [1, 5]}
        book.validate(book_data)

        author_id = book['author_ids'][0]
        logger.debug('author_id: %s' % author_id)

        (uri, params) = author_id.relations['full'].resolve(book_data, '/author_ids/0')
        self.assertEqual(uri, '/api/catalog/1.0/authors/1')

        (uri, params) = author_id.relations['full'].resolve(book_data, '/author_ids/1')
        self.assertEqual(uri, '/api/catalog/1.0/authors/5')
        
        author = self.r.resources['author']
        author_data = {'id': 1, 'name': 'John Q'}
        author.validate(author_data)

        (uri, params) = author.relations['books'].resolve(author_data)
        logger.debug('author.relations.books uri: %s %s' % (uri, params))


class TestSchemaBase(unittest.TestCase):

    def parse(self, string):
        d = yaml_loader.marked_load(string)
        return Schema.parse(d, 'root', api='/api')

    def check_valid(self, s, valid=None, invalid=None, toxml=False):
        if type(s) is str:
            schema = self.parse(s)
        else:
            schema = s
        
        for a in valid:
            try:
                schema.validate(a)
            except ValidationError, e:
                self.fail("ValidationError: value should pass: %s, %s" % (a, e))
            
            if toxml:
                schema.toxml(a)

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
            logger.debug('Got validation error: %s' % str(e))
            return
        self.fail('Schema should have thrown error, %s' % etype)


class TestJsonSchema(TestSchemaBase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_exceptions(self):
        # cover exception string output
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        try:
            Schema.parse(d)
        except ValidationError, e:
            self.assertIsNotNone(str(e))

    def test_missing_api(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        with self.assertRaises(ValidationError):
            Schema.parse(d)

    def test_unnamed(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        j = Schema.parse(d, api='/')
        self.assertTrue(j.name.startswith('element'))

    def test_unknown_type(self):
        s = "type: frobnosticator\n"
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
        schema = self.parse("type: object\n"
                            "properties:\n"
                            "    id: { type: number }\n"
                            "    name: { type: string }\n"
                            "    billing_address: { $ref: address }\n")
        with self.assertRaises(ParseError):
            schema.validate({'id': 2,
                             'name': 'Frozzle',
                             'billing_address': "doesn't exist"})

    def test_null(self):
        self.check_valid("type: 'null'\n",

                         # values to validate
                         valid=[None],

                         invalid=["11",
                                  11,
                                  [ 1, 2 ],
                                  "abc",
                                  "123",
                                  "1234512345"],
                         )
        
    def test_data(self):
        # missing 'content_type'
        self.check_bad_schema("type: data\n",
                              ParseError)

        self.check_valid("type: data\n"
                         "content_type: text\n"
                         "description: simple data\n",

                         # values to validate
                         valid=["aa",
                                "11",
                                "abc",
                                "123",
                                "1234512345"],

                         invalid=[]
                         )
        schema = self.parse("type: data\n"
                            "content_type: text\n"
                            "description: simple data\n")
        self.assertTrue(schema.is_simple())

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
                         "pattern: '^[a-z0-9]+$'\n",

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
                         "minLength: 2\n",

                         # values to validate
                         valid=["aa",
                                "1234512345" * 10],

                         invalid=["A"]
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

        schema = self.parse("type: string\n"
                            "minLength: 2\n"
                            "maxLength: 10\n"
                            "enum: [one, two, three]\n"
                            "pattern: '[a-z0-9]+'\n"
                            "default: 'one'\n")
        self.assertIsInstance(schema.str_detailed(), basestring)

    def test_number(self):
        self.check_valid("type: number\n"
                         "minimum: 2\n"
                         "maximum: 100\n",

                         valid=[2, 2.0, 2.5, 99, 100],
                         invalid=[1, 101, 0]
                         )

        self.check_valid("type: number\n"
                         "minimum: 2\n"
                         "maximum: 100\n"
                         "exclusiveMinimum: true\n"
                         "exclusiveMaximum: true\n",

                         valid=[2.01, 3, 99, 99.999],
                         invalid=[2, 100, 1]
                         )

        self.check_valid("type: number\n"
                         "enum: [1, 2, 3]\n",

                         valid=[1, 2, 3],
                         invalid=[0, 100, 4, 'one']
                         )

        schema = self.parse("type: number\n"
                            "minimum: 2\n"
                            "maximum: 100\n"
                            "enum: [2, 3, 4]\n"
                            "default: 3\n")
        self.assertIsInstance(schema.str_detailed(), basestring)

    def test_integer(self):
        self.check_valid("type: integer\n"
                         "minimum: 2\n"
                         "maximum: 100\n",

                         valid=[2, 99, 100],
                         invalid=[1, 101, 2.5, 99.1]
                         )

        self.check_valid("type: integer\n"
                         "minimum: 2\n"
                         "maximum: 100\n"
                         "exclusiveMinimum: true\n"
                         "exclusiveMaximum: true\n",

                         valid=[3, 99],
                         invalid=[2, 100, 1]
                         )

        self.check_valid("type: integer\n"
                         "enum: [1, 2, 3]\n",

                         valid=[1, 2, 3],
                         invalid=[0, 100, 4, 1.0, 'one']
                         )

        schema = self.parse("type: integer\n"
                            "minimum: 2\n"
                            "maximum: 100\n"
                            "enum: [2, 3, 4]\n"
                            "default: 3\n")
        self.assertIsInstance(schema.str_detailed(), basestring)

    def test_timestamp(self):
        self.check_valid("type: timestamp\n",

                         valid=[1234567890,
                                1234567890.123],
                         invalid=['foo',
                                  {'timestamp': 1234567890}]
                         )

        self.check_valid("type: timestamp-hp\n",

                         valid=[1234567890,
                                1234567890.123000],
                         invalid=['foo',
                                  {'timestamp': 1234567890}]
                         )

    def test_object_simple(self):
        self.check_valid("type: object\n"
                         "properties:\n"
                         "   foo: { type: number }\n"
                         "   bar: { type: string }\n"
                         "additionalProperties: false\n",

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

    def test_link(self):
        # missing self link with no path
        self.check_bad_schema("type: object\n"
                              "properties:\n"
                              "   foo: { type: number }\n"
                              "links:\n"
                              "   alink:\n"
                              "      method: GET\n",
                              ParseError)

        # extra link properties
        self.check_bad_schema("type: object\n"
                              "properties:\n"
                              "   foo: { type: number }\n"
                              "links:\n"
                              '   self: { path: "$/authors" }\n'
                              "   alink:\n"
                              "      invalid: GET\n",
                              ParseError)

        # invalid link properties
        self.check_bad_schema("type: object\n"
                              "properties:\n"
                              "   foo: { type: number }\n"
                              "links:\n"
                              '   self: { path: "$/authors" }\n'
                              "   alink:\n"
                              "      invalid\n",
                              ParseError)

        schema = self.parse("type: object\n"
                            "properties:\n"
                            "   foo: { type: number }\n"
                            "links:\n"
                            '   self: { path: "$/authors" }\n')
        link = schema.links['self']
        self.assertIsInstance(repr(link), str)

        # XXX investigate this API
        self.assertIsNone(link.find_by_id('/api', link.fullid()))
        self.assertIsNotNone(link.find_by_id('/api', 'root/links/self'))

class TestSchema(TestSchemaBase):

    def setUp(self):
        self.r = reschema.RestSchema()
        self.r.load(TEST_SCHEMA_YAML)

    def tearDown(self):
        self.r = None

    def test_object_required(self):
        r = self.r.resources['test_object_required']

        self.check_valid(r,

                         valid = [ {'prop_number': 1,
                                    'prop_array': [ 99, 98 ] },
                                   {'prop_number': 1,
                                    'prop_string': 'foo',
                                    'prop_array': [ 99, 98 ] },
                                   ],

                         invalid = [ 
                                     { 'prop_array': [ 99, 98 ] },
                                     { 'prop_array': [ 99, 98 ],
                                       'prop_string': 'foo' } ])
        
    def test_anyof1(self):
        r = self.r.resources['test_anyof1']
        self.check_valid(r,

                         valid = [ {'a1': 1, 'a2': 2},
                                   {'a3': 3, 'a4': 4} ],

                         invalid = [ {'a1': 3, 'a4': 4} ] )

        a1 = r['a1']
        self.assertEqual(a1.fullid(), '/test_anyof1/a1')

        a2 = r['a2']
        self.assertEqual(a2.fullid(), '/test_anyof1/a2')

        a2 = self.r.find('/test_anyof1/a2')
        self.assertEqual(a2.fullid(), '/test_anyof1/a2')

    def test_anyof2(self):
        r = self.r.resources['test_anyof2']
        self.check_valid(r,

                         valid = [ {'a1': 1, 'a2': 5},
                                   {'a1': 1, 'a2': 9},
                                   {'a1': 2, 'a2': 11},
                                   {'a1': 2, 'a2': 19},
                                   ],

                         invalid = [ {'a1': 3, 'a2': 4},
                                     {'a1': 1, 'a3': 5},
                                     {'a1': 1, 'a2': 4},
                                     {'a1': 1, 'a2': "foo"},
                                     {'a1': 1, 'a2': 10},
                                     {'a1': 2, 'a2': 4},
                                     {'a1': 2, 'a2': 5},
                                     {'a1': 2, 'a2': 9},
                                     {'a1': 2, 'a2': 29},
                                     ] )

        a1 = r['a1']
        self.assertEqual(a1.fullid(), '/test_anyof2/a1')

        a2 = r['a2']
        self.assertEqual(a2.fullid(), '/test_anyof2/a2')

        a2 = self.r.find('/test_anyof2/a2')
        self.assertEqual(a2.fullid(), '/test_anyof2/a2')

    def test_anyof3(self):
        r = self.r.resources['test_anyof3']
        self.check_valid(r,

                         valid = [ {'a1': 1, 'a2': 5},
                                   {'a1': 1, 'a2': 9},
                                   {'a1': 2, 'a2': 11},
                                   {'a1': 2, 'a2': 19},
                                   ],

                         invalid = [ {'a1': 3, 'a2': 4},
                                     {'a1': 1, 'a3': 5},
                                     {'a1': 1, 'a2': 4},
                                     {'a1': 1, 'a2': "foo"},
                                     {'a1': 1, 'a2': 10},
                                     {'a1': 2, 'a2': 4},
                                     {'a1': 2, 'a2': 5},
                                     {'a1': 2, 'a2': 9},
                                     {'a1': 2, 'a2': 29},
                                     ] )

        a2 = self.r.find('/test_anyof3/a2')
        self.assertEqual(a2.fullid(), '/test_anyof3/a2')

    def test_allof(self):
        r = self.r.resources['test_allof']
        self.check_valid(r,

                         valid = [ {'a1': 1,
                                    'a2': { 'a21_number': 2,
                                            'a21_string': 'foo' },
                                    'a3': 'f3'},

                                   {'a1': 2,
                                    'a2': { 'a22_number': 2,
                                            'a22_string': 'foo',
                                            'a22_array' : [ 1, 2, 3 ]},
                                    'a3': 'd1' },
                                   ],
                         
                         invalid = [ {'a1': 2,
                                      'a2': { 'a21_number': 2,
                                              'a21_string': 'foo' },
                                      'a3': 'f3'},

                                     {'a1': 1,
                                      'a2': { 'a21_numbe': 2,
                                              'a21_string': 'foo' },
                                      'a3': 'f3'},

                                     {'a1': 1,
                                      'a2': { 'a21_number': 2,
                                              'a21_string': 'foo',
                                              'a21_bad': 4 },
                                      'a3': 'f3'},
                                     ])

        self.assertEqual(r['/a2/a21_string'].fullid(),
                         '/test_allof/a2/a21_string')
        self.assertEqual(r['/a2/a22_number'].fullid(),
                         '/test_allof/a2/a22_number')
        self.assertEqual(r['/a2/a22_array/0'].fullid(),
                         '/test_allof/a2/a22_array/items')

    def test_oneof(self):
        r = self.r.resources['test_oneof']
        self.check_valid(r,

                         valid = [ {'a1': 1, 'a2': 21 }, 
                                   {'a1': 5, 'a2': 10 }, 
                                   ],

                         invalid = [ {'a1': 1, 'a2': 2 },
                                     {'a1': 5, 'a2': 20 },])

    def test_not(self):
        r = self.r.resources['test_not']
        self.check_valid(r,
                         valid = [1, 2, 3, 4, 6, 9, 10],
                         invalid = [0, 5, 7, 8, 11, 12, 13, 200] )

    def test_self_params(self):
        r = self.r.resources['test_self_params']
        self.check_valid(r,
                         valid = [ 1, 2 ],
                         invalid = ['one', '2'])
        
    def test_link_req_resp_defaults(self):
        r = self.r.resources['test_methods']

        self.check_valid(r.links['delete'].request,
                         valid=[None],
                         invalid=[{}, [], '', 0])
        self.check_valid(r.links['delete'].response,
                         valid=[None],
                         invalid=[{}, [], '', 0])

if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
