# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

"""
This module defines classes for handling <json-schema> style declarations.
The `Schema` class is the base for all type-specific class such as String,
Number, Object, etc.

The normal use case is to call Schema.parse() to generate a Schema object
from Python data structure.

Consider the following:

    >>> bookdef = {
        'type': 'object',
        'description': 'Book object',
        'properties' : {
           'id' : { 'type' : 'number' },
           'title' : { 'type' : 'string' },
           'author_ids' : {
              'type' : 'array',
              'items' : { 'type' : 'number' }
           }
        }

    >>> bookschema = Schema.parse(bookdef, name='book')

    >>> print bookschema.str_simple()
    book                           object               Book object
    book.author_ids                array
    book.author_ids.[items]        number
    book.id                        number
    book.title                     string

Note that 'Array' and 'Object' schemas link to children schemas
representing the array items and object properties respectively:

    >>> type(bookschema)
    reschema.jsonschema.Object

    >>> type(bookschema['id'])
    reschema.jsonschema.Number

    >>> type(bookschema['author_ids'])
    reschema.jsonschema.Array

    >>> type(bookschema['author_ids'][0])
    reschema.jsonschema.Number

The `validate` method will ensure that input data conforms to
a schema.  This method may be called on any Schema variant, and
it recursively validates the entire input data object as needed:

    >>> bookinput = {'id': 1, 'title': 'A good book!'}
    >>> bookschema.validate(bookinput)

    >>> bookinput = {'id': 1, 'title': 'A good book!',
                     'author_ids': ['bad author']}
    >>> bookschema.validate(bookinput)
    ValidationError: 'bad author' expected to be a number for
    book.author_ids.[items]

See each individual Schema type for the complete list of validation rules.
"""

import re
import copy
import logging
import xml.etree.ElementTree as ET
from collections import OrderedDict

import uritemplate
from jsonpointer import resolve_pointer, JsonPointer

from reschema.util import parse_prop, check_type
from reschema.reljsonpointer import resolve_rel_pointer
from reschema.exceptions import \
    ValidationError, MissingParameter, ParseError, InvalidReference

__all__ = ['Schema']

logger = logging.getLogger(__name__)

DEFAULT_REQ_RESP = {'type': 'null'}

# Map of 'json-schema' type to class that handles it
type_map = {}


def _register_type(cls):
    type_map[cls._type] = cls


def _check_input(name, input):
    """ Verify that input is empty, all keywords should have been parsed. """
    if input is None:
        return

    if not isinstance(input, dict):
        raise ParseError('%s: definition should be a dictionary, got: %s' %
                         (name, type(input)), input)

    badkeys = input.keys()
    if len(badkeys) > 0:
        raise ParseError('%s: unrecognized property in definition: %s' %
                         (name, ','.join(badkeys)), badkeys[0])


class Schema(object):
    """Base class for all JSON schema types."""

    # Counter used for assigning names/ids for anonymous types
    count = 1

    # Map of all known schemas by id
    schemas = {}

    def __init__(self, typestr, input, name=None,
                 parent=None, servicedef=None, id=None):
        """Create a new Schema object of the given `typestr`.

        :param typestr: the <json-schema> type

        :param input: the definition to parse

        :param parent: allows nesting of schemas, may be None

        :param name: a label for this schema

        :param servicedef: the servicedef instance this instance is
            assocaited with. If None, inherit from parent.

        :raises ValidationError: if neither `servicedef` nor `parent`
            is specified.

        :raises ParseError: if unexpected data or formats are
            encountered while parsing.
        """
        self._typestr = typestr
        self.parent = parent
        self.name = name
        self.id = id
        self.children = []

        if servicedef is None:
            if parent is None:
                raise ValidationError(
                    "Must specify 'servicedef' if parent is None", input)
            servicedef = parent.servicedef

        self.servicedef = servicedef

        parse_prop(self, input, 'label', name, valid_type=[str, unicode])
        parse_prop(self, input, 'description', '', valid_type=[str, unicode])
        parse_prop(self, input, 'notes', '', valid_type=[str, unicode])
        parse_prop(self, input, 'example')
        parse_prop(self, input, 'readOnly',
                   parent.readOnly if (parent and
                                       isinstance(parent, Schema)) else False,
                   valid_type=bool)

        parse_prop(self, input, 'xmlTag')
        parse_prop(self, input, 'xmlSchema')
        parse_prop(self, input, 'xmlExample')
        parse_prop(self, input, 'xmlKeyName')

        self.relations = OrderedDict()
        for key, value in parse_prop(None, input, 'relations', {},
                                     valid_type=dict).iteritems():
            check_type(key, value, dict)
            self.relations[key] = Relation(value, key, self,
                                           id=('%s/relations/%s' %
                                               (self.id, key)))

        self.links = OrderedDict()
        for key, value in parse_prop(None, input, 'links', {},
                                     valid_type=dict).iteritems():
            check_type(key, value, dict)
            self.links[key] = Link(value, key, self,
                                   id='%s/links/%s' % (self.id, key))

        self.anyof = []
        for i, subinput in enumerate(parse_prop(None, input, 'anyOf', [],
                                                valid_type=list)):
            s = Schema.parse(subinput, parent=self, name='anyOf[%d]' % i,
                             id='%s/anyOf/%d' % (self.id, i))
            self.anyof.append(s)
            self.children.append(s)

        self.allof = []
        for i, subinput in enumerate(parse_prop(None, input, 'allOf', [],
                                                valid_type=list)):
            s = Schema.parse(subinput, parent=self, name='allOf[%d]' % i,
                             id='%s/allOf/%d' % (self.id, i))
            self.allof.append(s)
            self.children.append(s)

        self.oneof = []
        for i, subinput in enumerate(parse_prop(None, input, 'oneOf', [],
                                                valid_type=list)):
            s = Schema.parse(subinput, parent=self, name='oneOf[%d]' % i,
                             id='%s/oneOf/%d' % (self.id, i))
            self.oneof.append(s)
            self.children.append(s)

        n = parse_prop(None, input, 'not', None)
        if n is not None:
            self.not_ = Schema.parse(n, parent=self, name='not',
                                     id='%s/not' % self.id)
            self.children.append(self.not_)
        else:
            self.not_ = None

        #print "Adding schema: %s - parent %s" % (self.fullid(), parent)
        self.schemas[self.fullid()] = self

    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__,
                                         self.fullid())

    @classmethod
    def parse(cls, input, name=None, parent=None, servicedef=None,
              id=None):
        """Parse a <json-schema> definition for an object.

        :param input: the definition to parse
        :type input: dict

        :param parent: allows nesting of schemas, may be None

        :param name: a label for this schema

        :param servicedef: the servicedef instance this instance is
            assocaited with. If None, inherit from parent.

        :raises ParseError: if unexpected data or formats are
            encountered while parsing.
        """

        if not isinstance(input, dict):
            raise ParseError(
                "Schema definition must be an object: %s%s" %
                ((parent.fullname() + '.') if parent else '', name),
                input)

        if name is None:
            name = parse_prop(None, input, 'label', valid_type=[str, unicode])
            if name is None:
                name = 'element%d' % cls.count
                cls.count = cls.count + 1

        if '$ref' in input:
            typestr = '$ref'
        elif 'type' not in input:
            typestr = 'multi'
        else:
            typestr = parse_prop(None, input, 'type', required=True,
                                 valid_type=[str, unicode])

        try:
            cls = type_map[typestr]
        except KeyError:
            msg = ('Unknown type: %s while parsing %s%s' %
                   (typestr, (parent.fullname() + '.') if parent else '',
                    name))
            raise ParseError(msg, typestr)

        return cls(input, name, parent, servicedef=servicedef, id=id)

    @classmethod
    def find_by_id(cls, id):
        """Find a schema by fullid."""

        if id in cls.schemas:
            return cls.schemas[id]

        return None

    @property
    def typestr(self):
        """The <json-schema> type for this schema."""
        return self._typestr

    def is_simple(self):
        """Returns True if this object is a simple data type.

        Simple data types have no linked children schema.  For example, Array
        and Object return False whereas String and Number return True.

        """
        return True
    def isSimple(self):
        """Compatibility method."""
        return self.is_simple()

    def is_ref(self):
        """Return True if this schema is a reference."""
        return False
    def isRef(self):
        """Compatibility method."""
        return self.is_ref()

    def is_multi(self):
        """Return True if this schema is a multi instance.

        Multi data types use the anyOf, oneOf or allOf properties
        to combine multiple schema definitions."""
        return False
    def isMulti(self):
        """Compatibility method."""
        return self.is_multi()

    def matches(self, other):
        """ Return True if other refers to the same schema based on 'self'. """
        return (('self' in self.links) and
                ('self' in other.links) and
                (self.links['self'].path.template ==
                 other.links['self'].path.template))

    def fullname(self):
        """Return the full printable name using dotted notation."""
        # TODO: Should this be cached?  Do we support changing it?
        if self.parent:
            if isinstance(self.parent, Array):
                return self.parent.fullname() + '[' + self.name + ']'
            else:
                return self.parent.fullname() + '.' + self.name

        return self.name

    def fullid(self, relative=False):
        """Return the full id using path notation.

        :param relative: set to True to return an id relative to this
            servicedef

        """
        return '%s%s' % (('' if relative else self.servicedef.id), self.id)

    def str_simple(self):
        """Return a string representation of this element as a basic table."""
        s = '%-30s %-20s %s\n' % (self.fullname(),
                                  self.typestr,
                                  self.description.split('\n')[0])
        for child in self.children:
            s += child.str_simple()
        for relation, value in self.relations.iteritems():
            s += value.str_simple()
        return s

    def str_detailed(self, additional_details=''):
        """Return a detailed string representation of this element."""
        s = self.fullname() + ':' + self.typestr + '\n'
        if self.description:
            s += 'Description: ' + self.description + '\n'

        if additional_details:
            s += additional_details

        s += '\n'

        for child in self.children:
            s += child.str_detailed()

        return s

    def validate(self, input):
        # Must validate every schema in the allOf array
        for s in self.allof:
            s.validate(input)

        # Must validate only one schema in the oneOf array
        if len(self.oneof) > 0:
            found = 0
            for s in self.oneof:
                try:
                    s.validate(input)
                    found = found + 1
                except ValidationError:
                    continue

            if found == 0:
                raise ValidationError(
                    "%s: input does not match any 'oneOf' schema" %
                    self.fullname(), self)
            elif found > 1:
                raise ValidationError(
                    "%s: input matches more than one 'oneOf' schemas",
                    self.fullname(), self)

        # Must validate at least one schema in the anyOf array
        if len(self.anyof) > 0:
            for s in self.anyof:
                try:
                    s.validate(input)
                except ValidationError:
                    continue
                return

            raise ValidationError(
                "%s: input does not match any 'anyOf' schema" %
                self.fullname(), self)

        # Must *not* validate the not schema
        if self.not_ is not None:
            try:
                self.not_.validate(input)
                valid = True
            except ValidationError:
                valid = False

            if valid:
                raise ValidationError(
                    "%s: input should not match 'not' schema" %
                    self.fullname(), self)

    def _pointer_part_to_index(self, part):
        # Subclasses can overried to type convert if needed.
        return part

    def by_pointer(self, pointer):
        """Index into a schema by breaking a data-based jsonpointer into parts.

        Appling this method to data that does not validate against this
        schema produces undefined results.

        :param pointer: The JSON pointer.  May be either absolute or relative.
        """
        if pointer in ('/', '0/'):
            # Special case root jsonpointer or relative pointer to self
            return self

        if pointer[0] == '/':
            # Absolute but non-root jsonpointer
            p = JsonPointer(pointer)
            index = self._pointer_part_to_index(p.parts[0])
            return self[index].by_pointer('/%s' % '/'.join(p.parts[1:]))

        m = re.match('^([0-9]+)(/.*)$', pointer)
        if m:
            # Looks like a relative jsonpointer
            uplevels = int(m.group(1))
            base_pointer = m.group(2)
            p = JsonPointer(base_pointer)
            o = self
            for i in range(uplevels):
                if o.parent is None:
                    raise KeyError(
                        ("%s cannot resolve '%s' as a relative JSON pointer, "
                         "not enough uplevels") % (self.fullname(), pointer))
                o = o.parent

            if len(p.parts) == 1 and p.parts[0] == '':
                return o
            return o.by_pointer(base_pointer)

        # TODO: Does this still make sense?
        #       Or should it be ValueError for json-pointer syntax?
        raise KeyError(pointer)

    def toxml(self, input, parent=None):
        """Generate an XML Element structure representing this element."""
        if parent is not None:
            parent.set(self.name, str(input))
            return parent
        else:
            elem = ET.Element(self.name)
            elem.text = str(input)
            return elem


class Multi(Schema):
    _type = 'multi'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Multi._type, input, name, parent, **kwargs)

        _check_input(self.fullname(), input)

    def __getitem__(self, name):
        # TODO: The previous implementation, in addition to ignoring the
        #       allOf and oneOf lists, was highly order-dependent.
        #       Factoring out by_pointer() somehow exposed this sufficiently
        #       to fail the unit tests (it is not clear how they were passing
        #       before), so for now call this not implemented and xfail
        #       the tests- consistent failure is better than
        #       non-deterministic failure.
        raise NotImplementedError

    def is_multi(self):
        return True

    @property
    def typestr(self):
        if len(self.children) == 0:
            return "any"
        return "multiple"

_register_type(Multi)


class Ref(Schema):
    _type = '$ref'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Ref._type, input, name, parent, **kwargs)

        # Lazy resolution because references may be used before they
        # are defined
        self._refschema = None
        ref_id = parse_prop(None, input, '$ref', required=True)
        try:
            self._refschema_id = self.servicedef.expand_id(ref_id)
        except InvalidReference as e:
            raise ParseError(str(e), ref_id)

        _check_input(self.fullname(), input)

    @property
    def refschema(self):
        if self._refschema is None:
            sch = Schema.find_by_id(self._refschema_id)
            if sch is None:
                sch = self.servicedef.find(self._refschema_id)
            if sch is None:
                raise InvalidReference(("%s $ref" % self.fullname()),
                                       self._refschema_id)

            # XXXCJ - Hopefully we can drop this deepcopy -- need to
            # make sure docs and sleepwalker don't rely on it
            #sch = copy.deepcopy(sch)
            #sch.parent = self
            #sch.parent.api = self.api

            self._refschema = sch
            for link in sch.links:
                if link not in self.links:
                    self.links[link] = sch.links[link]
            for relation in sch.relations:
                if relation not in self.relations:
                    self.relations[relation] = sch.relations[relation]

        return self._refschema

    @property
    def typestr(self):
        return self.refschema.name

    def is_simple(self):
        return False

    def is_ref(self):
        """Return True if this schema is a reference."""
        return True

    def validate(self, input):
        self.refschema.validate(input)

    def toxml(self, input, parent=None):
        return self.refschema.toxml(input, parent)

    def __getitem__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return self.refschema.__getitem__(name)

    def __getattr__(self, name):
        return getattr(self.refschema, name)

    def by_pointer(self, pointer):
        """Index into a schema by breaking a data-based jsonpointer into parts."""
        return self.refschema.by_pointer(pointer)

_register_type(Ref)


class Null(Schema):
    _type = 'null'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Null._type, input, name, parent, **kwargs)

        _check_input(self.fullname(), input)

    def validate(self, input):
        if (input is not None):
            raise ValidationError("%s should be None, got '%s'" %
                                  (self.fullname(), type(input)), self)
        super(Null, self).validate(input)

_register_type(Null)


class Boolean(Schema):
    _type = 'boolean'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Boolean._type, input, name, parent, **kwargs)
        parse_prop(self, input, 'default')

        _check_input(self.fullname(), input)

    def validate(self, input):
        if (type(input) is not bool):
            raise ValidationError("%s should be a boolean, got '%s'" %
                                  (self.fullname(), type(input)), self)
        super(Boolean, self).validate(input)

_register_type(Boolean)


class String(Schema):
    _type = 'string'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, String._type, input, name, parent, **kwargs)
        parse_prop(self, input, 'minLength', valid_type=int)
        parse_prop(self, input, 'maxLength', valid_type=int)
        parse_prop(self, input, 'pattern')
        parse_prop(self, input, 'enum')
        parse_prop(self, input, 'default')

        _check_input(self.fullname(), input)

    def validate(self, input):
        if len(str(input)) > 40:
            trunc = str(input)[:40] + "..."
        else:
            trunc = str(input)

        if (not isinstance(input, str) and not isinstance(input, unicode)):
            raise ValidationError("%s: input must be a string, got %s: %s" %
                                  (self.fullname(), type(input), trunc), self)

        if (self.minLength is not None) and len(input) < self.minLength:
            raise ValidationError(
                "%s: input must be at least %d chars, got %d: %s" %
                (self.fullname(), self.minLength, len(input), trunc), self)

        if (self.maxLength is not None) and len(input) > self.maxLength:
            raise ValidationError(
                "%s: input must be no more than %d chars, got %d: %s" %
                (self.fullname(), self.maxLength, len(input), trunc), self)

        if (self.pattern is not None) and (not re.match(self.pattern, input)):
            raise ValidationError(
                "%s: input failed pattern match %s: %s" %
                (self.fullname(), self.pattern, trunc), self)

        if (self.enum is not None) and (input not in self.enum):
            raise ValidationError(
                "%s: input not a valid enumeration value: %s" %
                (self.fullname(), trunc), self)
        super(String, self).validate(input)

    def str_detailed(self):
        s = ''
        if self.minLength or self.maxLength:
            s += 'Length:'
            if self.minLength:
                s += ' min %d' % self.minLength
            if self.maxLength:
                s += ' max %d' % self.maxLength
            s += '\n'
        if self.pattern:
            s += 'Pattern: %s\n' % self.pattern
        if self.enum:
            s += 'Valid values: %s\n' % self.enum
        if self.default:
            s += 'Default value: %s\n' % self.default
        return super(String, self).str_detailed(additional_details=s)
_register_type(String)


class NumberOrInteger(Schema):
    _type = 'number'

    def __init__(self, type, allowed_types, input, name, parent, **kwargs):
        Schema.__init__(self, type, input, name, parent, **kwargs)
        self.allowed_types = allowed_types
        parse_prop(self, input, 'minimum', valid_type=allowed_types)
        parse_prop(self, input, 'maximum', valid_type=allowed_types)
        parse_prop(self, input, 'exclusiveMinimum', valid_type=bool,
                   default_value=False)
        parse_prop(self, input, 'exclusiveMaximum', valid_type=bool,
                   default_value=False)
        parse_prop(self, input, 'default', valid_type=allowed_types)
        parse_prop(self, input, 'enum', valid_type=list)

        _check_input(self.fullname(), input)

    def validate(self, input):
        if not any(isinstance(input, t) for t in self.allowed_types):
            raise ValidationError("%s should be a number, got '%s'" %
                                  (self.fullname(), type(input)), self)

        if self.minimum is not None:
            if self.exclusiveMinimum:
                if not (input > self.minimum):
                    raise ValidationError(
                        "%s: input must be > minimum %d, got %d" %
                        (self.fullname(), self.minimum, input), self)
            else:
                if not (input >= self.minimum):
                    raise ValidationError(
                        "%s: input must be >= minimum %d, got %d" %
                        (self.fullname(), self.minimum, input), self)

        if self.maximum is not None:
            if self.exclusiveMaximum:
                if not (input < self.maximum):
                    raise ValidationError(
                        "%s: input must be < maximum %d, got %d" %
                        (self.fullname(), self.maximum, input), self)
            else:
                if not (input <= self.maximum):
                    raise ValidationError(
                        "%s: input must be <= maximum %d, got %d" %
                        (self.fullname(), self.maximum, input), self)

        if (self.enum is not None) and (input not in self.enum):
            raise ValidationError(
                "%s: input not a valid enumeration value: %s" %
                (self.fullname(), input), self)
        super(NumberOrInteger, self).validate(input)

    def str_detailed(self):
        s = ''
        if self.minimum or self.maximum:
            s += 'Range: '
            if self.minimum is not None:
                s += ' min %d' % self.minimum
            if self.maximum is not None:
                s += ' max %d' % self.maximum
            s += '\n'
        if self.enum:
            s += 'Valid values: %s\n' % self.enum
        if self.default:
            s += 'Default value: %s\n' % self.default
        return super(NumberOrInteger, self).str_detailed(additional_details=s)


class Number(NumberOrInteger):
    _type = 'number'

    def __init__(self, input, name, parent, **kwargs):
        super(Number, self).__init__(self._type, (int, float), input,
                                     name, parent, **kwargs)

_register_type(Number)


class Integer(NumberOrInteger):
    _type = 'integer'

    def __init__(self, input, name, parent, **kwargs):
        super(Integer, self).__init__(self._type, (int,), input,
                                      name, parent, **kwargs)

_register_type(Integer)


class Timestamp(Schema):
    _type = 'timestamp'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Timestamp._type, input, name, parent, **kwargs)
        _check_input(self.fullname(), input)

    def validate(self, input):
        if not any(isinstance(input, t) for t in (int, float)):
            raise ValidationError("'%s' expected to be a number for %s" %
                                  (input, self.fullname()), self)
        super(Timestamp, self).validate(input)

_register_type(Timestamp)


class TimestampHP(Schema):
    _type = 'timestamp-hp'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, TimestampHP._type, input, name, parent, **kwargs)
        _check_input(self.fullname(), input)

    def validate(self, input):
        if not any(isinstance(input, t) for t in (int, float)):
            raise ValidationError("'%s' expected to be a number for %s" %
                                  (input, self.fullname()), self)
        super(TimestampHP, self).validate(input)

_register_type(TimestampHP)


class Object(Schema):
    _type = 'object'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Object._type, input, name, parent, **kwargs)
        self.properties = OrderedDict()

        for prop, value in parse_prop(None, input, 'properties', {},
                                      valid_type=dict).iteritems():
            c = Schema.parse(value, prop, self,
                             id='%s/properties/%s' % (self.id, prop))
            self.properties[prop] = c
            self.children.append(c)

        parse_prop(self, input, 'required')

        ap = parse_prop(None, input, 'additionalProperties',
                        valid_type=[dict, bool])
        if ap in (None, True):
            ap = {}
        if type(ap) is bool:
            self.additional_properties = ap
        else:
            ap_name = ap['label'] if ('label' in ap) else 'prop'
            c = Schema.parse(ap, '<%s>' % ap_name, self,
                             id='%s/additionalProperties' % (self.id))
            self.additional_properties = c
            self.children.append(c)

        _check_input(self.fullname(), input)

    def __getitem__(self, name):
        if name in self.properties:
            return self.properties[name]
        if self.additional_properties is not False:
            return self.additional_properties
        # Be lazy about generating the right kind of exception:
        self.properties[name]

    def is_simple(self):
        return False

    def validate(self, input):
        if not isinstance(input, dict):
            raise ValidationError("%s should be an object, got '%s'" %
                                  (self.fullname(), type(input)), self)

        for k in input:
            if k in self.properties:
                self.properties[k].validate(input[k])
            elif self.additional_properties is False:
                raise ValidationError("'%s' is not a valid property for %s" %
                                      (k, self.fullname()), self)
            elif isinstance(self.additional_properties, Schema):
                self.additional_properties.validate(input[k])

        if self.required is not None:
            for k in self.required:
                if k not in input:
                    raise ValidationError(
                        "Missing required property '%s' for '%s'" %
                        (k, self.fullname()), self)
        super(Object, self).validate(input)

    def toxml(self, input, parent=None):
        """Return ElementTree object with `input` data.

        Additional Properties that are not explicitly defined are not
        supported.

        """
        if parent is not None:
            elem = ET.SubElement(parent, self.name)
        else:
            elem = ET.Element(self.name)

        for k in input:
            if k not in self.properties:
                if self.additional_properties is False:
                    raise ValueError('Invalid property: %s' % k)

                subobj = copy.copy(self.additional_properties)
                keyname = subobj.xmlKeyName or 'key'

                if subobj.is_simple():
                    subelem = ET.SubElement(elem, subobj.name)
                    subelem.set(keyname, k)

                    subelem.text = str(input[k])
                else:
                    subelem = subobj.toxml(input[k])
                    subelem.set(keyname, k)
                    elem.append(subelem)

            else:
                prop = self.properties[k]
                prop.toxml(input[k], elem)

        return elem
_register_type(Object)


class Array(Schema):
    _type = 'array'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Array._type, input, name, parent, **kwargs)

        items = parse_prop(None, input, 'items', required=True)
        if 'label' in items:
            childname = items['label']
        else:
            childname = 'items'
        self.items = Schema.parse(items, childname, self,
                                  id='%s/items' % self.id)
        self.children.append(self.items)

        parse_prop(self, input, 'minItems')
        parse_prop(self, input, 'maxItems')

        _check_input(self.fullname(), input)

    def is_simple(self):
        return False

    @property
    def typestr(self):
        return 'array of <%s>' % self.items.typestr

    def __getitem__(self, name):
        # Use internal function for convenience even if not pointer part.
        # This is just to get the right exception on both code paths.
        self._pointer_part_to_index(name)
        return self.items

    def _pointer_part_to_index(self, part):
        try:
            index = int(part)
        except ValueError:
            raise TypeError("list indices must be integers, not %r" %
                            type(part).__name__)
        return index

    def validate(self, input):
        if not isinstance(input, list):
            raise ValidationError("%s should be an array, got '%s'" %
                                  (self.fullname(), type(input)), self)

        for o in input:
            self.items.validate(o)

        super(Array, self).validate(input)

    def toxml(self, input, parent=None):
        if parent is not None:
            elem = ET.SubElement(parent, '%s' % self.name)
        else:
            elem = ET.Element(self.name)

        for o in input:
            subelem = self.children[0].toxml(o)
            elem.append(subelem)
        return elem
_register_type(Array)


class Data(Schema):
    _type = 'data'

    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Data._type, input, name, parent, **kwargs)

        parse_prop(self, input, 'content_type', required=True)
        parse_prop(self, input, 'description')

        _check_input(self.fullname(), input)

    def validate(self, input):
        # any value will pass, regardless of content_type set
        # validation of that type of data seems beyond the scope of reschema
        pass

    def is_simple(self):
        return True
_register_type(Data)


class Relation(object):

    def __init__(self, input, name, schema, id):
        self.name = name
        self.schema = schema
        self.vars = None
        self.id = id

        # Lazy resolution because references may be used before they
        # are defined
        self._resource = None
        ref_id = parse_prop(None, input, 'resource', required=True)
        self._resource_id = schema.servicedef.expand_id(ref_id)

        self.vars = parse_prop(self, input, 'vars')

        _check_input(self.fullname(), input)

    def __str__(self):
        return self.resource.name

    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__,
                                         self.fullid())

    def is_ref(self):
        return False

    def is_multi(self):
        return False

    @property
    def resource(self):
        if self._resource is None:
            sch = Schema.find_by_id(self._resource_id)
            if sch is None:
                sch = self.schema.servicedef.find(self._resource_id)
            if sch is None:
                raise InvalidReference(("%s resource" % self.fullname()),
                                       self._resource_id)
            self._resource = sch
        return self._resource

    def fullname(self):
        return self.schema.fullname() + '.relations.' + self.name

    def fullid(self, relative=False):
        """Return the full id using path notation.

        :param relative: set to True to return an id relative to this
            servicedef

        """
        return '%s%s' % (('' if relative else self.schema.servicedef.id),
                         self.id)

    def str_simple(self):
        return '%-30s %-20s\n' % (self.fullname(), '<relation>')

    def resolve(self, data, fragment=None, params=None):
        """ Resolves this path against data and params.

        Returns a tuple (path, values) where path is this path
        template resolved against the passed `data` and
        `params`.  The return `values` is the dictionary
        of vars defined for the path and the resolved
        values for these vars.

        """
        target_self = self.resource.links['self']
        target_params = target_self._params

        if params:
            vals = params
        else:
            vals = {}

        if data is not None:
            if self.vars is not None:
                for var, relp in self.vars.iteritems():
                    vals[var] = resolve_rel_pointer(data, fragment or '', relp)

        (uri, values) = target_self.path.resolve(vals)

        params = {}
        if target_params:
            for var, schema in target_params.iteritems():
                if var in vals:
                    schema.validate(vals[var])
                    params[var] = vals[var]

        return (uri, params, values)


class Link(object):

    def __init__(self, input, name, schema, id):
        self.name = name
        self.schema = schema
        self.servicedef = schema.servicedef
        self.id = id

        parse_prop(self, input, 'description', '')
        parse_prop(self, input, 'notes', '')
        parse_prop(self, input, 'example')
        parse_prop(self, input, 'method')
        parse_prop(self, input, 'authorization')

        pathdef = parse_prop(None, input, 'path')
        if pathdef is not None:
            self.path = Path(self, pathdef)
        elif self.method is not None:
            if 'self' not in self.schema.links:
                raise ParseError(("Link '%s' defined with no path and "
                                  "schema has no 'self' link") %
                                 str(self), input)
            self.path = self.schema.links['self'].path
        else:
            self.path = None

        self._request = None
        if 'request' in input:
            self._request = Schema.parse(parse_prop(None, input, 'request'),
                                         parent=self, name='request',
                                         id='%s/request' % self.id)
        elif name != 'self':
            # Must deepcopy because of how parse_prop() works later on.
            self._request = Schema.parse(copy.deepcopy(DEFAULT_REQ_RESP),
                                         parent=self, name='request',
                                         id='%s/request' % self.id)

        self._response = None
        if 'response' in input:
            self._response = Schema.parse(parse_prop(None, input, 'response'),
                                          parent=self, name='response',
                                          id='%s/response' % self.id)
        elif name != 'self':
            # Must deepcopy because of how parse_prop() works later on.
            self._response = Schema.parse(copy.deepcopy(DEFAULT_REQ_RESP),
                                          parent=self, name='response',
                                          id='%s/response' % self.id)

        if name == 'self':
            self._params = {}
            if 'params' in input:
                for key, value in parse_prop(None, input, 'params',
                                             {}, valid_type=dict).iteritems():
                    self._params[key] = Schema.parse(value, parent=self,
                                                     name=key,
                                                     id=('%s/params/%s' %
                                                         (self.id, key)))

        _check_input(self.fullname(), input)

    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__,
                                         self.fullid())

    def is_ref(self):
        return False

    def is_multi(self):
        return False

    def fullname(self):
        return self.schema.fullname() + '.links.' + self.name

    def fullid(self, relative=False):
        """Return the full id using path notation.

        :param relative: set to True to return an id relative to this
            servicedef

        """
        return '%s%s' % (('' if relative else self.schema.servicedef.id),
                         self.id)

    def str_simple(self):
        return '%-30s %-20s %s\n' % (self.fullname(), '<link>',
                                     self.description)

    @property
    def request(self):
        r = self._request
        if type(r) is Ref:
            r = r.refschema
        return r

    @property
    def response(self):
        r = self._response
        if type(r) is Ref:
            r = r.refschema
        return r


class Path(object):
    """The `Path` class manages URI templates and resolves variables.

    The `resolve` method supports resolving variables in the template from
    a data object conforming to the linked schema.

    When creating a path, the `pathdef` may take one of two forms:

      1) pathdef = '<uri-template>'

      2) pathdef = { 'template': '<uri-template'>,
                     'vars' : {
                        '<var1>' : <rel-json-pointer>,
                        '<var2>' : <rel-json-pointer>,
                        ... } }

    In both cases, the '<uri-template>' is follows RFC6570 syntax.
    Variables in the template are resolved first looking to vars, then
    do the data object.

    Since URI templates can only specify simple variables, the second
    form is used as a level of indirection to move up or down in a
    data structure relative to the place where the link was defined.

    """

    def __init__(self, link, pathdef):
        """Create a `Path` associated with `link`."""

        self.link = link

        self.pathdef = pathdef
        self.vars = None

        if isinstance(pathdef, dict):
            self.template = pathdef['template']
            self.vars = pathdef['vars']
        else:
            self.template = pathdef
            self.vars = None

    def __str__(self):
        return self.template

    def resolve(self, data, pointer=None):
        """Resolve variables in template from `data` relative to `pointer`."""
        values = {}
        if data:
            values['$'] = resolve_pointer(data, pointer or '')

            if self.vars:
                for v in self.vars:
                    values[v] = resolve_rel_pointer(data,
                                                    pointer or '',
                                                    self.vars[v])

            if data and isinstance(data, dict):
                for v in data.keys():
                    if v not in values:
                        values[v] = data[v]

        tmpl = self.template
        logger.debug("%s template: %s" % (self.link.fullname(), tmpl))
        required = set(uritemplate.variables(self.template))
        have = set(values.keys())
        if not required.issubset(have):
            raise MissingParameter(
                "Missing parameters for link '%s' path template '%s': %s" %
                (self.link.name, self.template, [x for x in
                                                 required.difference(have)]),
                self)

        uri = uritemplate.expand(self.template, values)

        return (uri, values)
