# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import logging
import unittest
import pytest
import urlparse

from yaml.error import MarkedYAMLError

import reschema

from reschema.exceptions import (ValidationError, NoManager,
                                 MissingParameter, ParseError,
                                 InvalidReference)

from reschema.jsonschema import (Object, Integer, String, Array, Schema)
from reschema import yaml_loader, ServiceDef, ServiceDefManager

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yaml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yaml')

PACKAGE_PATH = os.path.dirname(TEST_PATH)

EXAMPLES_DIR = os.path.join(PACKAGE_PATH, 'examples')
BOOKSTORE_YAML = os.path.join(EXAMPLES_DIR, 'bookstore.yaml')
BOOKSTORE_JSON = os.path.join(EXAMPLES_DIR, 'bookstore.json')


class TestReschema(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_schema(self):
        # Test marked load and dropping descriptions
        reschema.settings.MARKED_LOAD = True
        reschema.settings.LOAD_DESCRIPTIONS = False
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        self.assertEqual(r.name, 'bookstore')
        self.assertEqual(r.check_references(), [])

        info = r.resources['info']
        self.assertTrue(hasattr(info.input, 'start_mark'))
        self.assertEqual(info.description, '')

        info_descr = info.by_pointer('/description')
        self.assertEqual(info_descr.default, 'Info Description')

        address = r.types['address']
        city = address.by_pointer('/city')
        self.assertEqual(city.description, '')

        # Test unmarked load and not loading descriptions (defaults)
        reschema.settings.MARKED_LOAD = False
        reschema.settings.LOAD_DESCRIPTIONS = True
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        self.assertEqual(r.name, 'bookstore')
        self.assertEqual(r.check_references(), [])

        info = r.resources['info']
        self.assertFalse(hasattr(info.input, 'start_mark'))
        self.assertNotEqual(info.description, '')

        info_descr = info.by_pointer('/description')
        self.assertEqual(info_descr.default, 'Info Description')

        address = r.types['address']
        city = address.by_pointer('/city')
        self.assertNotEqual(city.description, '')

    def test_load_schema_json(self):
        reschema.settings.MARKED_LOAD = True
        r = ServiceDef()
        r.load(BOOKSTORE_JSON)
        self.assertEqual(r.name, 'bookstore')
        info = r.resources['info']
        self.assertTrue(hasattr(info.input, 'start_mark'))

        reschema.settings.MARKED_LOAD = False
        r = ServiceDef()
        r.load(BOOKSTORE_JSON)
        self.assertEqual(r.name, 'bookstore')
        info = r.resources['info']
        self.assertFalse(hasattr(info.input, 'start_mark'))

    def test_unknown_schema(self):
        import tempfile
        fd, name = tempfile.mkstemp(suffix='.txt', text=True)

        try:
            f = os.fdopen(fd, 'w')
            f.write('testingdata')
            f.close()

            r = ServiceDef()
            with self.assertRaises(ValueError):
                r.load(name)
        finally:
            os.unlink(name)

    def test_parse_schema(self):
        r = ServiceDef()
        with open(BOOKSTORE_YAML, 'r') as f:
            r.parse_text(f.read(), format='yaml')
        self.assertEqual(r.name, 'bookstore')

    def test_parse_schema_json(self):
        r = ServiceDef()
        with open(BOOKSTORE_JSON, 'r') as f:
            r.parse_text(f.read())
        self.assertEqual(r.name, 'bookstore')

    def test_load_bad_schema(self):
        with open(BOOKSTORE_YAML, 'r') as f:
            schema = f.readlines()
        for i, line in enumerate(schema):
            if "type: object" in line:
                schema.insert(i-1, '      bad_object_name: foo\n')
                break

        r = ServiceDef()
        with self.assertRaises(MarkedYAMLError):
            r.parse_text(''.join(schema), format='yaml')

    def test_resource_load(self):
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        self.assertEquals(len(r.resources), 8)
        self.assertIn('info', r.resources)
        self.assertIn('author', r.resources)
        self.assertIn('authors', r.resources)
        self.assertTrue(r.find_resource('author'))
        self.assertEquals(r.find_type('no_resource'), None)

    def test_type_load(self):
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        self.assertIn('address', r.types)
        self.assertTrue(r.find_type('address'))
        self.assertEquals(r.find_type('no_type'), None)

    def test_resource_objects(self):
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        a = r.resources['author']
        self.assertFalse(a.is_ref())
        self.assertFalse(a.is_simple())
        self.assertIn('id', a.properties)
        self.assertIn('name', a.properties)
        self.assertEqual(a.fullid(True), '#/resources/author')
        self.assertIsNone(a.parent)
        resources = [x for x in r.resource_iter()]
        self.assertEqual(len(resources), 8)

    def test_find_name_basic(self):
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        a = ServiceDef.find(r, '#/resources/author')
        self.assertEqual(a.fullid(True), '#/resources/author')

    def test_find_name_complex(self):
        r = ServiceDef()
        r.load(BOOKSTORE_YAML)
        c = ServiceDef.find(r, '#/resources/book/chapters')
        self.assertEqual(c.fullid(True),
                         '#/resources/book/properties/chapters')
        self.assertEqual(c._type, 'array')
        self.assertEqual(c.typestr, 'array of <object>')
        c = ServiceDef.find(r, '#/resources/book/chapters/1')
        self.assertEqual(c.fullid(True),
                         '#/resources/book/properties/chapters/items')
        self.assertEqual(c._type, 'object')
        c = ServiceDef.find(r, '#/resources/book/author_ids')
        self.assertEqual(c._type, 'array')
        c = ServiceDef.find(r, '#/resources/book/author_ids/1')
        self.assertEqual(c._type, 'integer')


class TestBookstore(unittest.TestCase):

    def setUp(self):
        self.r = ServiceDef()
        self.r.load(BOOKSTORE_YAML)

    def tearDown(self):
        self.r = None

    def test_string(self):
        s = self.r.resources['author'].properties['name']
        self.assertFalse(s.is_ref())
        self.assertTrue(s.is_simple())

        # successful validation will return None
        self.assertIsNone(s.validate('foo'))
        self.assertIsNone(s.validate(u'bar'))

        with self.assertRaises(ValidationError):
            s.validate(42)

    def test_integer(self):
        n = self.r.resources['author'].properties['id']
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
        pub = ServiceDef.find(self.r, '#/resources/publisher')
        ref = pub.properties['billing_address']
        self.assertFalse(ref.is_simple())
        self.assertTrue(ref.is_ref())
        self.assertEqual(ref.typestr, 'address')

    def test_link_target(self):
        s = self.r.resources['author']
        link = s.relations['instances']
        self.assertEqual(link.resource, self.r.resources['authors'])

    def test_link_path(self):
        pub = ServiceDef.find(self.r, '#/resources/publisher')
        link = pub.links['self']
        path = link.path
        self.assertEqual(str(path), '$/publishers/{id}')
        (resolved_path, values) = path.resolve({'id': 12})
        return self.assertEqual(resolved_path, '$/publishers/12')

    def test_link_template_path(self):
        book = ServiceDef.find(self.r, '#/resources/book')
        chapters = book.properties['chapters']
        items = chapters.items
        book_chapter = items.relations['full']
        data = {'book': book.example}
        (uri, values) = book_chapter.resolve(data, '/book/chapters/1')
        self.assertEqual(uri, '$/books/100/chapters/2')
        with self.assertRaises(MissingParameter):
            book_chapter.resolve(None)

    def test_object(self):
        # skip validation, we are checking that elsewhere
        s = self.r.resources['author']
        self.assertFalse(s.is_ref())
        self.assertFalse(s.is_simple())
        self.assertIsInstance(repr(s), str)

    def test_object_xml(self):
        book = ServiceDef.find(self.r, '#/resources/book')
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
        self.assertEqual(sorted(xml.keys()),
                         [u'id', u'publisher_id', u'title'])
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

        a = book['author_ids']
        self.assertEqual(type(a), Array)
        self.assertEqual(book.by_pointer('/author_ids'), a)

        # Test JSON pointer syntax
        self.assertEqual(type(book['author_ids'][0]), Integer)
        self.assertEqual(book.by_pointer('/author_ids/0'),
                         book['author_ids'][0])

        # Test relative JSON pointer syntax
        a0 = book.by_pointer('/author_ids/0')
        self.assertEqual(a0.by_pointer('/'), a0)
        self.assertEqual(a0.by_pointer('2/'), book)
        self.assertEqual(a0.by_pointer('2/id'), book['id'])

        with self.assertRaises(KeyError):
            book['foo']

        with self.assertRaises(KeyError):
            book.by_pointer('1/')

        with self.assertRaises(TypeError):
            a['a']

        with self.assertRaises(TypeError):
            a['10a']

        with self.assertRaises(KeyError):
            a0.by_pointer('3/')

        # Unlike book, auther does not specify additionalProperties
        author = self.r.resources['author']
        Schema.parse({}, name='<prop>', parent=author)
        self.assertEqual(author['randomjunk'], author.additional_properties)
        self.assertEqual(author.additional_properties,
                         author.children[-1])


class TestBookstoreLinks(unittest.TestCase):

    def setUp(self):
        self.r = ServiceDef()
        self.r.load(BOOKSTORE_YAML)

    def tearDown(self):
        self.r = None

    def test_links(self):
        book = self.r.resources['book']
        book_data = {'id': 1, 'title': 'My first book',
                     'publisher_id': 5, 'author_ids': [1, 5]}
        book.validate(book_data)

        author_id = book['author_ids'][0]
        logger.debug('author_id: %s' % author_id)

        (uri, values) = (author_id
                                 .relations['full']
                                 .resolve(book_data, '/author_ids/0'))

        self.assertEqual(uri, '$/authors/1')

        (uri, values) = (author_id
                                 .relations['full']
                                 .resolve(book_data, '/author_ids/1'))

        self.assertEqual(uri, '$/authors/5')

        author = self.r.resources['author']
        author_data = {'id': 1, 'name': 'John Q'}
        author.validate(author_data)

        (uri, values) = (author
                                 .relations['books']
                                 .resolve(author_data))

        logger.debug('author.relations.books uri: %s %s'
                     % (uri, values))


class TestSchemaBase(unittest.TestCase):

    def parse(self, string):
        d = yaml_loader.marked_load(string)
        s = ServiceDef(manager=ServiceDefManager())
        s.id = 'http://support.riverbed.com/apis/testschema/1.0'
        return Schema.parse(d, 'root', servicedef=s, id='#/resources/foo')

    def check_valid(self, s, valid=None, invalid=None, toxml=False):
        if type(s) is str:
            schema = self.parse(s)
        else:
            schema = s

        for a in valid:
            try:
                schema.validate(a)
            except ValidationError, e:
                self.fail("ValidationError: value should pass: %s, %s" %
                          (a, e))

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
        self.servicedef = reschema.ServiceDef(manager=ServiceDefManager())
        self.servicedef.id = 'http://support.riverbed.com/apis/testschema/1.0'

    def test_exceptions(self):
        # cover exception string output
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        try:
            Schema.parse(d)
        except ValidationError, e:
            self.assertIsNotNone(str(e))

    def test_missing_servicedef(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        with self.assertRaises(ValidationError):
            Schema.parse(d)

    def test_unnamed(self):
        s = "type: boolean\n"
        d = yaml_loader.marked_load(s)
        j = Schema.parse(d, servicedef=self.servicedef)
        self.assertTrue(j.name.startswith('element'))

    def test_unknown_type(self):
        s = "type: frobnosticator\n"
        d = yaml_loader.marked_load(s)
        with self.assertRaises(ParseError):
            Schema.parse(d)

    def test_empty(self):
        e = Schema.parse({}, servicedef=self.servicedef)
        self.check_valid(e,
                         valid=[None,
                                True,
                                False,
                                -1,
                                9999999.33333333,
                                'some string',
                                ['array', 42, {}],
                                {'object': 'stuff', 'nmber': 2}],
                         invalid=[])

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

    def test_ref_parse_error(self):
        with self.assertRaises(ParseError):
            self.parse("type: object\n"
                       "properties:\n"
                       "    id: { type: number }\n"
                       "    name: { type: string }\n"
                       "    billing_address: { type: striing }\n")

    def test_ref_invalid(self):
        schema = self.parse("type: object\n"
                            "properties:\n"
                            "    id: { type: number }\n"
                            "    name: { type: string }\n"
                            "    billing_address: { $ref: '#/address' }\n")

        with self.assertRaises(InvalidReference):
            schema.validate({'id': 2,
                             'name': 'Frozzle',
                             'billing_address': "doesn't exist"})

    def test_no_manager(self):
        schema = self.parse("type: object\n"
                            "properties:\n"
                            "    id: { type: number }\n"
                            "    name: { type: string }\n"
                            "    billing_address:"
                            " { $ref: '/api/other/1.0#/types/address' }\n")
        schema.servicedef.manager = None
        with self.assertRaises(NoManager):
            schema.validate({'id': 2,
                             'name': 'Frozzle',
                             'billing_address': "doesn't exist"})

    def test_null(self):
        self.check_valid("type: 'null'\n",

                         # values to validate
                         valid=[None],

                         invalid=["11",
                                  11,
                                  [1, 2],
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
        self.check_valid("type: number\n",
                         valid=[0, 1, 1.0, long(1), -1, -1.0, long(-1)],
                         invalid=['hi', True, False])

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
        self.check_valid("type: integer\n",
                         valid=[0, 1, long(1), -1, long(-1)],
                         invalid=[1.0, float(1), -1.0, float(-1), 'hi'])

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
                                1234567890.123,
                                long(1)],
                         invalid=['foo',
                                  {'timestamp': 1234567890},
                                  True, False]
                         )

        self.check_valid("type: timestamp-hp\n",

                         valid=[1234567890,
                                1234567890.123000,
                                long(1)],
                         invalid=['foo',
                                  {'timestamp': 1234567890},
                                  True, False]
                         )

    def test_object_simple(self):
        # required field not a list
        self.check_bad_schema("type: object\n"
                              "required: foo\n"
                              "properties:\n"
                              "  foo: { type: number }\n"
                              "  bar: { type: number }\n",
                              ParseError)

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

        # missing method on non-self link
        self.check_bad_schema("type: object\n"
                              "properties:\n"
                              "   foo: { type: number }\n"
                              "links:\n"
                              "   self: { path: '$/authors' }\n"
                              "   nomethod:\n"
                              "      response: { type: integer }",
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

    def test_empty_tags(self):
        """
        Verify tags member is added even if not specified in schema
        """

        # Base Schema-derived types
        schemas = ["type: integer",
                   "type: number",
                   "type: boolean",
                   "type: string",
                   "type: 'null'",
                   "type: timestamp",
                   "type: timestamp-hp",

                   ("type: array\n"
                    "items: { type: number }"),

                   ("type: object\n"
                    "properties:\n"
                    "   foo: { type: string }")]

        for schema in schemas:
            parsed = self.parse(schema)
            self.assertEquals(parsed.tags, {})

        # Links and relations
        schema = self.parse("type: integer\n"
                            "links:\n"
                            "   self: { path: $/foo }\n"
                            "relations:\n"
                            "   foo:\n"
                            "      resource: /foo")

        self.assertEquals(schema.links['self'].tags, {})
        self.assertEquals(schema.relations['foo'].tags, {})

        # Typeless schema fragment
        schema = self.parse("oneOf:\n"
                            "- type: integer\n"
                            "- type: 'null'")
        self.assertEquals(schema.tags, {})

    def test_tags(self):
        """
        Verify tags behavior
        """

        # tag-not-a-dict: Schema-derived types, links, and relations
        self.check_bad_schema("type: integer\n"
                              "tags: hi\n",
                              ParseError)

        self.check_bad_schema("type: integer\n"
                              "tags: [ hi ]\n",
                              ParseError)

        self.check_bad_schema("type: integer\n"
                              "links:\n"
                              "  self:\n"
                              "    path: /foo\n"
                              "    tags: [ hi ]",
                              ParseError)

        self.check_bad_schema("type: integer\n"
                              "relations:\n"
                              "  foo:\n"
                              "    resource: /foo\n"
                              "    tags: [ hi ]",
                              ParseError)

        # Base Schema-derived types
        schemas = [("type: integer\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: number\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: boolean\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: string\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: 'null'\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: timestamp\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: timestamp-hp\n"
                    "tags: { hi: ~, quit: bye }"),

                   ("type: array\n"
                    "tags: { hi: ~, quit: bye }\n"
                    "items:\n"
                    "    type: number"),

                   ("type: object\n"
                    "tags: { hi: ~, quit: bye }\n"
                    "properties:\n"
                    "   foo: { type: string }")]

        for schema in schemas:
            parsed = self.parse(schema)
            self.assertEquals(parsed.tags, {'hi': None, 'quit': 'bye'})

        # Links and relations
        schema = self.parse("type: integer\n"
                            "links:\n"
                            "   self:\n"
                            "      path: $/foo\n"
                            "      tags: { linktag: ~ }\n"
                            "relations:\n"
                            "   foo:\n"
                            "      resource: /foo\n"
                            "      tags: { relationtag: ~ }")

        self.assertEquals(schema.links['self'].tags, {'linktag': None})
        self.assertEquals(schema.relations['foo'].tags, {'relationtag': None})

        # Schema fragment that uses oneOf/etc to define itself as allowing
        # multiple types
        schema = self.parse("oneOf:\n"
                            "- type: integer\n"
                            "- type: 'null'\n"
                            "tags: { This is my tag: ~ }")
        self.assertEquals(schema.tags, {'This is my tag': None})


class TestSchema(TestSchemaBase):

    def setUp(self):
        self.r = reschema.ServiceDef()
        self.r.load(SERVICE_DEF_TEST)

    def tearDown(self):
        self.r = None

    def test_check_references(self):
        self.assertEqual(self.r.check_references(), [])

    def test_object_required(self):
        r = self.r.resources['test_object_required']

        self.check_valid(r,

                         valid=[{'prop_number': 1,
                                 'prop_array': [99, 98]},
                                {'prop_number': 1,
                                 'prop_string': 'foo',
                                 'prop_array': [99, 98]},
                                ],

                         invalid=[{'prop_array': [99, 98]},
                                  {'prop_array': [99, 98],
                                   'prop_string': 'foo'}])

    def test_anyof1_validation(self):
        r = self.r.resources['test_anyof1']
        self.check_valid(r,

                         valid=[{'a1': 1, 'a2': 2},
                                {'a3': 3, 'a4': 4}],

                         invalid=[{'a1': 3, 'a4': 4}])

    @pytest.mark.xfail
    def test_anyof1_indexing(self):
        r = self.r.resources['test_anyof1']

        a1 = r.by_pointer('/anyOf/0/properties/a1')
        self.assertEqual(a1.fullid(True),
                         '#/test_anyof1/anyOf/0/properties/a1')

        a2 = r['a2']
        self.assertEqual(a2.fullid(), '/test_anyof1/a2')

        a2 = ServiceDef.find(self.r, '#/resources/test_anyof1/a2')
        self.assertEqual(a2.fullid(), '#/resources/test_anyof1/a2')

    def test_anyof2_validation(self):
        r = self.r.resources['test_anyof2']
        self.check_valid(r,

                         valid=[{'a1': 1, 'a2': 5},
                                {'a1': 1, 'a2': 9},
                                {'a1': 2, 'a2': 11},
                                {'a1': 2, 'a2': 19}],

                         invalid=[{'a1': 3, 'a2': 4},
                                  {'a1': 1, 'a3': 5},
                                  {'a1': 1, 'a2': 4},
                                  {'a1': 1, 'a2': "foo"},
                                  {'a1': 1, 'a2': 10},
                                  {'a1': 2, 'a2': 4},
                                  {'a1': 2, 'a2': 5},
                                  {'a1': 2, 'a2': 9},
                                  {'a1': 2, 'a2': 29}]
                         )

    @pytest.mark.xfail
    def test_anyof2_indexing(self):
        r = self.r.resources['test_anyof2']
        a1 = r['a1']
        self.assertEqual(a1.fullid(), '/test_anyof2/a1')

        a2 = r['a2']
        self.assertEqual(a2.fullid(), '/test_anyof2/a2')

        a2 = ServiceDef.find(self.r, '/test_anyof2/a2')
        self.assertEqual(a2.fullid(), '/test_anyof2/a2')

    def test_anyof3(self):
        r = self.r.resources['test_anyof3']
        self.check_valid(r,

                         valid=[{'a1': 1, 'a2': 5},
                                {'a1': 1, 'a2': 9},
                                {'a1': 2, 'a2': 11},
                                {'a1': 2, 'a2': 19}],

                         invalid=[{'a1': 3, 'a2': 4},
                                  {'a1': 1, 'a3': 5},
                                  {'a1': 1, 'a2': 4},
                                  {'a1': 1, 'a2': "foo"},
                                  {'a1': 1, 'a2': 10},
                                  {'a1': 2, 'a2': 4},
                                  {'a1': 2, 'a2': 5},
                                  {'a1': 2, 'a2': 9},
                                  {'a1': 2, 'a2': 29}])

        a2 = ServiceDef.find(self.r, '#/resources/test_anyof3/a2')
        self.assertEqual(a2.fullid(True),
                         '#/resources/test_anyof3/properties/a2')

    def test_allof_validation(self):
        r = self.r.resources['test_allof']
        self.check_valid(r,

                         valid=[{'a1': 1,
                                 'a2': {'a21_number': 2,
                                        'a21_string': 'foo'},
                                 'a3': 'f3'},

                                {'a1': 2,
                                 'a2': {'a22_number': 2,
                                        'a22_string': 'foo',
                                        'a22_array': [1, 2, 3]},
                                 'a3': 'd1'}],

                         invalid=[{'a1': 2,
                                   'a2': {'a21_number': 2,
                                          'a21_string': 'foo'},
                                   'a3': 'f3'},

                                  {'a1': 1,
                                   'a2': {'a21_numbe': 2,
                                          'a21_string': 'foo'},
                                   'a3': 'f3'},

                                  {'a1': 1,
                                   'a2': {'a21_number': 2,
                                          'a21_string': 'foo',
                                          'a21_bad': 4},
                                   'a3': 'f3'}]
                         )

    @pytest.mark.xfail
    def test_allof_indexing(self):
        r = self.r.resources['test_allof']
        self.assertEqual(r.by_pointer('/a2/a21_string').fullid(True),
                         '#/resources/test_allof/a2/a21_string')
        self.assertEqual(r.by_pointer('/a2/a22_number').fullid(True),
                         '#/resources/test_allof/a2/a22_number')
        self.assertEqual(r.by_pointer('/a2/a22_array/0').fullid(True),
                         '#/resources/test_allof/a2/a22_array/items')

    def test_oneof(self):
        r = self.r.resources['test_oneof']
        self.check_valid(r,

                         valid=[{'a1': 1, 'a2': 21},
                                {'a1': 5, 'a2': 10}],

                         invalid=[{'a1': 1, 'a2': 2},
                                  {'a1': 5, 'a2': 20}])

    def test_not(self):
        r = self.r.resources['test_not']
        self.check_valid(r,
                         valid=[1, 2, 3, 4, 6, 9, 10],
                         invalid=[0, 5, 7, 8, 11, 12, 13, 200])

    def test_link_req_resp_defaults(self):
        r = self.r.resources['test_methods']

        self.check_valid(r.links['delete'].request,
                         valid=[None],
                         invalid=[{}, [], 0, '', ' '])
        self.check_valid(r.links['delete'].response,
                         valid=[None],
                         invalid=[{}, [], 0, '', ' '])

    def test_array_constraints(self):
        r = self.r.resources['test_array_min']

        self.check_valid(r,
                         valid=[range(10), range(15)],
                         invalid=[range(0), range(9)])

        r = self.r.resources['test_array_max']

        self.check_valid(r,
                         valid=[range(0), range(10)],
                         invalid=[range(11)])

        r = self.r.resources['test_array_min_max']

        self.check_valid(r,
                         valid=[range(10), range(20)],
                         invalid=[range(0), range(9), range(21)])

    def test_self_params(self):
        r = self.r.resources['test_self_params']
        self.check_valid(r,
                         valid=[1, 2],
                         invalid=['one', '2'])
        l = r.links['self']

        # Resolution of path params using kvs
        (uri, kvs) = l.path.resolve(kvs={'x': 1, 'y': 2, 'z': 3})
        test_uri = '$/test_self_params?x=1&y=2&z=3'
        r1 = urlparse.parse_qs(urlparse.urlsplit(uri).query)
        r2 = urlparse.parse_qs(urlparse.urlsplit(test_uri).query)
        self.assertEqual(r1, r2)

    def test_self_vars(self):
        r = self.r.resources['test_self_vars']
        self.check_valid(r,
                         valid=[1, 2],
                         invalid=['one', '2'])
        l = r.links['self']

        # Resolution of path vars using vars
        (uri, kvs) = l.path.resolve(kvs={'x': 1, 'y': 2, 'z': 3})
        self.assertEqual(uri, '$/test_self_vars?x=1&y=2&z=3')

    def test_self_buried_vars(self):
        r = self.r.resources['test_self_buried_vars']
        l = r.links['self']

        # Classic resolution of all path variables using
        # a data representation
        (uri, kvs) = l.path.resolve(
            data={'id1': 3, 'buried': {'id2': 'foo'}})
        self.assertEqual(uri, '$/test_self_buried_vars/3/foo')

        # Override of 'id2' via kvs
        (uri, kvs) = l.path.resolve(
            data={'id1': 3, 'buried': {'id2': 'foo'}},
            kvs={'id2': 'bar'})
        self.assertEqual(uri, '$/test_self_buried_vars/3/bar')

        # Override of 'id1' via kvs
        (uri, kvs) = l.path.resolve(
            data={'id1': 3, 'buried': {'id2': 'foo'}},
            kvs={'id1': 4})
        self.assertEqual(uri, '$/test_self_buried_vars/4/foo')

        # Only use kvs
        (uri, kvs) = l.path.resolve(
            kvs={'id1': 4, 'id2': 'bar'})
        self.assertEqual(uri, '$/test_self_buried_vars/4/bar')

        # Missing parameters cases
        with self.assertRaises(MissingParameter):
            (uri, values) = l.path.resolve()

        with self.assertRaises(MissingParameter):
            (uri, values) = l.path.resolve(
                data={'id1': 3, 'buried': {'id3': 'foo'}})

        with self.assertRaises(MissingParameter):
            (uri, values) = l.path.resolve(
                data={'id3': 3, 'buried': {'id2': 'foo'}})

        with self.assertRaises(MissingParameter):
            (uri, values) = l.path.resolve(
                kvs={'id1': 5})

    def test_self_vars_rel(self):
        r = self.r.resources['test_self_vars_rel']
        rel = r.relations['rel']
        (uri, values) = rel.resolve(
            data={'var_id1': 3, 'var_id2': 'foo'})
        self.assertEqual(uri, '$/test_self_buried_vars/3/foo')

        (uri, values) = rel.resolve(
            kvs={'id1': 3, 'id2': 'foo'})
        self.assertEqual(uri, '$/test_self_buried_vars/3/foo')

        (uri, values) = rel.resolve(
            data={'var_id1': 3, 'var_id2': 'foo'},
            kvs={'id1': 4})
        self.assertEqual(uri, '$/test_self_buried_vars/4/foo')

        with self.assertRaises(MissingParameter):
            (uri, values) = rel.resolve(data=None)

        with self.assertRaises(MissingParameter):
            (uri, values) = rel.resolve(data=None, kvs={'v': 3})

        with self.assertRaises(MissingParameter):
            (uri, values) = rel.resolve(data={'v': 3})

    def test_uri_params(self):
        r = self.r.resources['test_uri_params']
        l = r.links['self']

        # Classic resolution of all path variables using
        # a data representation
        (uri, kvs) = l.path.resolve(
            data={'id': 3, 'meta': {'offset': 10, 'limit': 20}})
        self.assertEqual(uri, '$/test_uri_params/3?offset=10&limit=20')

        # Missing offset or limit should not be a problem as it is optional
        (uri, kvs) = l.path.resolve(
            data={'id': 3})
        self.assertEqual(uri, '$/test_uri_params/3')

        (uri, kvs) = l.path.resolve(
            data={'id': 3, 'meta': {'offset': 10}})
        self.assertEqual(uri, '$/test_uri_params/3?offset=10')

        (uri, kvs) = l.path.resolve(
            data={'id': 3, 'meta': {'limit': 20}})
        self.assertEqual(uri, '$/test_uri_params/3?limit=20')

        # Specify limit via kvs
        (uri, kvs) = l.path.resolve(
            data={'id': 3}, kvs={'limit': 5})
        self.assertEqual(uri, '$/test_uri_params/3?limit=5')

        # Add in page limit via kvs
        (uri, kvs) = l.path.resolve(
            data={'id': 3}, kvs={'limit': 5, 'page': 7})
        self.assertEqual(uri, '$/test_uri_params/3?limit=5&page=7')

        (uri, kvs) = l.path.resolve(
            data={'id': 3}, kvs={'page': 7})
        self.assertEqual(uri, '$/test_uri_params/3?page=7')

        # Check validation
        with self.assertRaises(ValidationError):
            (uri, kvs) = l.path.resolve(
                data={'id': 3, 'meta': {'offset': '10f', 'limit': 20}},
                validate=True)

        with self.assertRaises(ValidationError):
            (uri, kvs) = l.path.resolve(
                data={'id': 3}, kvs={'page': '7'}, validate=True)

        with self.assertRaises(ValidationError):
            (uri, kvs) = l.path.resolve(
                data={'id': 3}, kvs={'page': '7'}, validate=True)

class TestSchemaMerge(TestSchemaBase):

    def setUp(self):
        self.s = ServiceDef()
        self.s.load(SERVICE_DEF_TEST)
        manager = ServiceDefManager()
        manager.add(self.s)

    def test_merge(self):
        r = self.s.find('#/resources/test_merge')
        (self.check_valid(r,
                          valid=[{'val': 10}, {'val': 14}, {'val': 20}],
                          invalid=[{'val': 9}, {'val': 21}]))

    def test_merge_source_ref(self):
        r = self.s.find('#/resources/test_merge_source_ref')
        (self.check_valid(r,
                          valid=[{'p1': 10}, {'p1': 14}, {'p1': 20}],
                          invalid=[{'p1': 9}, {'p1': 21}]))

        # Verify that the original type's input was not modified
        # by the merge operation
        t = self.s.find('#/types/type_object')
        self.assertFalse('links' in t.input)

    def test_merge_with_ref(self):
        r = self.s.find('#/resources/test_merge_with_ref')
        (self.check_valid(r,
                          valid=[{'p1': 10}, {'p1': 14}, {'p1': 20}],
                          invalid=[{'p1': 9}, {'p1': 21}]))

    def test_merge_double_ref(self):
        r = self.s.find('#/resources/test_merge_double_ref')
        (self.check_valid(r,
                          valid=[10, 14, 20],
                          invalid=[9, 21]))

    def test_merge_merge(self):
        r = self.s.find('#/resources/test_merge_merge')
        (self.check_valid(r,
                          valid=[{'val': 15}, {'val': 20}],
                          invalid=[{'val': 9}, {'val': 10},
                                   {'val': 14}, {'val': 21}]))


class TestSchemaRef(TestSchemaBase):

    def setUp(self):
        self.s1 = ServiceDef()
        self.s1.load(SERVICE_DEF_TEST)
        self.s2 = ServiceDef()
        self.s2.load(SERVICE_DEF_TEST_REF)
        manager = ServiceDefManager()
        manager.add(self.s1)
        manager.add(self.s2)
        self.assertEqual(self.s1.check_references(), [])
        self.assertEqual(self.s2.check_references(), [])

    def test_ref_type(self):
        r1 = self.s2.find('#/resources/test_ref_type')
        (self.check_valid(r1,
                          valid=[{'val': 10}, {'val': 14}, {'val': 20}],
                          invalid=[{'val': 9}, {'val': 21}]))

        r2 = r1.relations['full'].resource
        (self.check_valid(r2,
                          valid=[{'val': 10}, {'val': 14}, {'val': 20}],
                          invalid=[{'val': 9}, {'val': 21}]))

        r3 = self.s2.find('#/resources/test_ref_type_full')

        self.assertTrue(r3.matches(r2))

    def test_ref_remote_types(self):
        r = self.s2.find('#/resources/test_ref_remote_types')

        (self.check_valid(r,
                          valid=[{'prop_boolean': True,
                                  'prop_number_limits': 12},
                                 {'prop_boolean': True,
                                  'prop_number_limits': 19}],

                          invalid=[{'prop_boolean': 1,
                                    'prop_number_limits': 12},
                                   {'prop_boolean': True,
                                    'prop_number_limits': 22},
                                   {'prop_boolean': False,
                                    'prop_number_limits': 19}]))

    def test_ref_relations(self):
        item = self.s1.find('#/resources/test_item')
        ref_resource = self.s2.find('#/resources/test_ref_remote_resource')
        ref_resource_item = ref_resource.relations['item'].resource

        self.assertEqual(item, ref_resource_item)

    def test_merge_remote_ref_ref(self):
        r = self.s2.find('#/resources/test_merge_remote_ref_ref')

        self.check_valid(r,
                         valid=[{'p1': True, 'p2': 12},
                                {'p1': True, 'p2': 19}],

                         invalid=[{'p1': 1, 'p2': 12},
                                  {'p1': True, 'p2': 'foo'}])


class TestLoadHook(TestSchemaBase):

    def setUp(self):
        class Hook(object):
            service_map = {
                'http://support.riverbed.com/apis/test/1.0':
                SERVICE_DEF_TEST,

                'http://support.riverbed.com/apis/test.ref/1.0':
                SERVICE_DEF_TEST_REF
                }

            def find_by_id(self, id_):
                if id_ in self.service_map:
                    s = ServiceDef.create_from_file(self.service_map[id_])
                    return s
                else:
                    raise KeyError("Invalid id: %s" % id_)

            def find_by_name(self, name, version, provider):
                assert(provider == 'riverbed')
                sid = ('http://support.riverbed.com/apis/%s/%s' %
                       (name, version))
                return self.find_by_id(sid)

        self.manager = ServiceDefManager()
        self.manager.add_load_hook(Hook())

    def tearDown(self):
        self.manager = None

    def test_find_by_id(self):
        sid = 'http://support.riverbed.com/apis/test.ref/1.0'
        s = self.manager.find_by_id(sid)
        self.assertEqual(s.id, sid)

    def test_find_by_name(self):
        sid = 'http://support.riverbed.com/apis/test.ref/1.0'
        s = self.manager.find_by_name('test.ref', '1.0')
        self.assertEqual(s.id, sid)
        s2 = self.manager.find_by_name('test.ref', '1.0')
        self.assertEqual(s2, s)

    def test_load(self):
        s = self.manager.find_by_id(
            'http://support.riverbed.com/apis/test.ref/1.0')
        rid = ('http://support.riverbed.com/apis/test/1.0'
               '#/types/type_boolean')
        r = s.find(rid)
        self.assertEqual(r.fullid(), rid)

        rid = ('http://support.riverbed.com/apis/test.ref/1.0'
               '#/resources/test_ref_remote_types')
        r = s.find(rid)
        self.assertEqual(r.fullid(), rid)

    def test_load_on_relation(self):
        s = self.manager.find_by_id(
            'http://support.riverbed.com/apis/test.ref/1.0')
        r = s.resources['test_ref_remote_types']

        sb = r.by_pointer('/prop_boolean')
        self.assertEqual(sb.fullid(),
                         ('http://support.riverbed.com/apis/test/1.0'
                          '#/types/type_boolean'))

        r = ServiceDef.find(s, '/apis/test/1.0#/resources/test_boolean')
        self.assertEqual(r.fullid(),
                         ('http://support.riverbed.com/apis/test/1.0'
                          '#/resources/test_boolean'))


class TestServiceDef(unittest.TestCase):

    SERVICE_DEF_TEMPLATE = """
$schema: {schema_id}
id: {id}
provider: {provider}
name: {name}
version: {version}
title: {title}
tags: {tags}
"""

    def create_service(self, **kwargs):
        schema_vars = {
            'schema_id': "'http://support.riverbed.com/apis/service_def/2.2'",
            'id': "'http://support.riverbed.com/apis/test/1.0'",
            'provider': "'riverbed'",
            'name': "'test'",
            'version': "'1.0'",
            'title': "'Test REST API'",
            'tags': {}
            }
        schema_vars.update(kwargs)
        text = self.SERVICE_DEF_TEMPLATE.format(**schema_vars)
        servicedef = ServiceDef.create_from_text(text, format='yaml')
        return servicedef

    def test_good(self):
        self.create_service()

    def test_numeric_version(self):
        with self.assertRaises(ParseError):
            self.create_service(version=1.0)

    def test_service_tags(self):
        """
        Verify top-level tag behavior
        """

        service_def = self.create_service()
        self.assertEquals(service_def.tags, {})

        service_def = self.create_service(tags='{hi: ~, quit: bye}')
        self.assertEquals(service_def.tags, {'hi': None, 'quit': 'bye'})


class TestI18N(unittest.TestCase):

    def setUp(self):
        self.r = ServiceDef()
        self.r.load(BOOKSTORE_YAML)

    def tearDown(self):
        self.r = None

    def test_unicode(self):

        book = self.r.resources['book']
        book_data = {'id': 1, 'title': u'\u6d4b\u8bd5',
                     'publisher_id': 5, 'author_ids': [1, 5]}
        book.validate(book_data)


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
