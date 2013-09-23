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

    >>> bookinput = {'id': 1, 'title': 'A good book!', author_ids: ['bad author']}
    >>> bookschema.validate(bookinput)
    ValidationError: 'bad author' expected to be a number for book.author_ids.[items]

See each individual Schema type for the complete list of validation rules.
"""

import re
import copy
import logging
import xml.etree.ElementTree as ET
from collections import OrderedDict

import uritemplate
from jsonpointer import resolve_pointer, JsonPointer

from reschema.util import parse_prop
from reschema.reljsonpointer import resolve_rel_pointer, RelJsonPointer

logger = logging.getLogger(__name__)

# Map of 'json-schema' type to class that handles it
type_map = {}
def _register_type(cls):
    type_map[cls._type] = cls
    
class ValidationError(Exception): pass
class MissingParameter(Exception): pass
class ParseError(Exception): pass

__all__ = ['Schema']

def _check_input(name, input):
    """ Verify that input is empty, all keywords should have been parsed. """
    if input is None:
        return
    
    if not isinstance(input, dict):
        raise ValidationError('%s: definition should be a dictionary, got: %s' % 
                              (name, type(input)))

    badkeys = input.keys()
    if len(badkeys) > 0:
        raise ValidationError('%s: unrecognized properites in definition: %s' % (name, ','.join(badkeys)))


class Schema(object):
    """Base class for all JSON schema types."""

    # Counter used for assigning names/ids for anonymous types
    count=1

    # Map of all known schemas:
    #   schemas["<api>/schema#<fullid>"] -> Schema
    schemas = {}

    def __init__(self, typestr, input, name=None, parent=None, api=None):
        """Create a new Schema object of the given `typestr`.

            `typestr` is the <json-schema> type

            `input` is the definition to parse

            `parent` allows nesting of schemas, may be None

            `name` is a label for this schema

            `api` is the base address for api calls

        If `api` is None, the parent's api is used.

        """
        self._typestr = typestr
        self.parent = parent
        self.name = name
        self.children = []
        
        if api is None:
            if parent is None:
                raise ValueError("Must specify 'api' if parent is None")
            api = parent.api

        self.api = api

        parse_prop(self, input, 'description', '')
        parse_prop(self, input, 'notes', '')
        parse_prop(self, input, 'id', name)
        parse_prop(self, input, 'required')
        parse_prop(self, input, 'example')
        parse_prop(self, input, 'readOnly')
        
        parse_prop(self, input, 'xmlTag')
        parse_prop(self, input, 'xmlSchema')
        parse_prop(self, input, 'xmlExample')
        parse_prop(self, input, 'xmlKeyName')

        self.relations = OrderedDict()
        for key, value in parse_prop(None, input, 'relations', {}, checkType=dict).iteritems():
            #logger.debug("Schema %s: adding relation '%s'" % (str(self), key))
            self.relations[key] = Relation(value, key, self)
            
        self.links = OrderedDict()
        for key, value in parse_prop(None, input, 'links', {}, checkType=dict).iteritems():
            #logger.debug("Schema %s: adding link '%s'" % (str(self), key))
            self.links[key] = Link(value, key, self)
            
        self.schemas[self.fullid(api=True)] = self

    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__, self.fullid())
    
    @classmethod
    def parse(cls, input, name=None, parent=None, api=None):
        """Parse a <json-schema> definition for an object.

            `input` is the definition to parse

            `parent` allows nesting of schemas, may be None

            `name` is a label for this schema

            `api` is the base address for api calls

        If `api` is None, the parent's api is used.
            
        """
    
        if name is None:
            name = parse_prop(None, input, 'id')
            if name is None:
                name = 'element%d' % cls.count
                cls.count = cls.count + 1
            
        if '$ref' in input:
            typestr = '$ref'
        else:
            typestr = parse_prop(None, input, 'type', required=True)

        if typestr in type_map:
            cls = type_map[typestr]
            return cls(input, name, parent, api=api)
        else:
            raise ValueError('Unknown type: %s while parsing %s%s' %
                             (typestr, (parent.fullname() + '.') if parent else '', name))

        
    @classmethod
    def find_by_id(cls, api, id):
        """Find a schema by fullid."""

        for pre in ['', '/types/', '/schemas/']:
            fullid = '%s/schema#/%s%s' % (api, pre, id)
            if fullid in cls.schemas:
                return cls.schemas[fullid]

        return None

    @property
    def typestr(self):
        """The <json-schema> type for this schema."""
        return self._typestr
    
    def isSimple(self):
        """Returns True if this object is a simple data type.

        Simple data types have no linked children schema.  For example, Array
        and Object return True whereas String and Number return False.

        """
        return True

    def isRef(self):
        """Return True if this schema is a reference."""
        return False

    
    def fullname(self):
        """Return the full printable name using dotted notation."""
        if self.parent:
            if isinstance(self.parent, Array):
                return self.parent.fullname() + '[' + self.name + ']'
            else:
                return self.parent.fullname() + '.' + self.name

        return self.name

    def fullid(self, api=False):
        """Return the full id using path notation.

        Include the api path if `api` is true.

        """
        # xxxcj - used to be (self.id or self.name), not sure if that's needed
        if self.parent:
            return self.parent.fullid(api) + '/' + self.id
        return ((self.api + '/schema#/') if api else '/') + self.id

    def str_simple(self):
        """Return a string representation of this element as a basic table."""
        s = '%-30s %-20s %s\n' % (self.fullname(), self.typestr, self.description.split('\n')[0])
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

        if self.required is not None:
            s += 'Requried: %s\n' % self.required
        if additional_details:
            s += additional_details

        s += '\n'
        
        for child in self.children:
            s += child.str_detailed()

        return s

    def __getitem__(self, name):
        if name == 'relations':
            return self.relations

        if name == 'links':
            return self.links

        if name == '/':
            # Special case jsonpointer
            return self
        
        if name[0] == '/':
            # treat 'name' as a jsonpointer
            p = JsonPointer(name)
            o = self
            for part in p.parts:
                o = o[part]
            return o

        m = re.match('^([0-9]+)(/.*)$', name)
        if m:
            # looks like a relative jsonpointer
            uplevels = int(m.group(1))
            p = JsonPointer(m.group(2))
            o = self
            for i in range(uplevels):
                if o.parent is None:
                    raise KeyError(("%s cannot resolve '%s' as a relative JSON pointer, " +
                                   "not enough uplevels") % (self.fullname(), name))
                o = o.parent
                    
            if len(p.parts) == 1 and p.parts[0] == '':
                return o
            
            for part in p.parts:
                o = o[part]

            return o

        raise KeyError(name)
    
    def toxml(self, input, parent=None):
        """Generate an XML Element structure representing this element."""
        if parent is not None:
            parent.set(self.id, str(input))
            return parent
        else:
            elem = ET.Element(self.id)
            elem.text = str(input)
            return elem


class Ref(Schema):
    _type = '$ref'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Ref._type, {}, name, parent, **kwargs)
        self._refschema = None
        self.refschema_id = parse_prop(None, input, '$ref', required=True)
        parse_prop(self, input, 'description', '')
        parse_prop(self, input, 'notes', '')
        parse_prop(self, input, 'id', '')

        _check_input(self.fullname(), input)

    @property
    def refschema(self):
        if self._refschema is None:
            self._refschema = Schema.find_by_id(self.api, self.refschema_id)
            if self._refschema is None:
                raise KeyError("No such schema '%s' for '$ref': %s" % (self.refschema_id, self.fullname()))
        return self._refschema
    
    def isSimple(self):
        return False

    def isRef(self):
        """Return True if this schema is a reference."""
        return True

    @property
    def typestr(self):
        return self.refschema.id
    
    def prettyPrint(self, recurse=False):
        Schema.prettyPrint(self, recurse=False)

    def validate(self, input):
        self.refschema.validate(input)

    def toxml(self, input, parent=None):
        return self.refschema.toxml(input, parent)

_register_type(Ref)


class Boolean(Schema):
    _type = 'boolean'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Boolean._type, input, name, parent, **kwargs)

        _check_input(self.fullname(), input)

    def validate(self, input):
        if (type(input) is not bool):
            raise ValidationError("%s should be a boolean, got '%s'" %
                                  (self.fullname(), type(input)))
_register_type(Boolean)


class String(Schema):
    _type = 'string'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, String._type, input, name, parent, **kwargs)
        parse_prop(self, input, 'minLength', checkType=int )
        parse_prop(self, input, 'maxLength', checkType=int )
        parse_prop(self, input, 'pattern')
        parse_prop(self, input, 'enum')
        parse_prop(self, input, 'default')

        _check_input(self.fullname(), input)

    def validate(self, input):
        if len(str(input)) > 40:
            trunc = str(input)[:40] + "..."
        else:
            trunc = str(input)

        if (type(input) not in [str, unicode]):
            raise ValidationError("%s: input must be a string, got %s: %s" %
                                  (self.fullname(), type(input), trunc))

        if (self.minLength is not None) and len(input) < self.minLength:
            raise ValidationError("%s: input must be at least %d chars, got %d: %s" %
                                  (self.fullname(), self.minLength, len(input), trunc))

        if (self.maxLength is not None) and len(input) > self.maxLength:
            raise ValidationError("%s: input must be no more than %d chars, got %d: %s" %
                                  (self.fullname(), self.maxLength, len(input), trunc))


        if (self.pattern is not None) and (not re.match('^' + self.pattern + '$', input)):
            raise ValidationError("%s: input failed pattern match %s: %s" %
                                  (self.fullname(), self.pattern, trunc))

        if (self.enum is not None) and (input not in self.enum):
            raise ValidationError("%s: input not a valid enumeration value: %s" %
                                  (self.fullname(), trunc))
            
            
    def schema_details(self):
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
        return super(String, self).schema_details(s)
_register_type(String)


class Number(Schema):
    _type = 'number'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Number._type, input, name, parent, **kwargs)
        parse_prop(self, input, 'minimum')
        parse_prop(self, input, 'maximum')
        parse_prop(self, input, 'exclusiveMinimum')
        parse_prop(self, input, 'exclusiveMaximum')
        parse_prop(self, input, 'default')
        parse_prop(self, input, 'enum')

        _check_input(self.fullname(), input)

    def validate(self, input):
        if (type(input) not in [int, float]):
            raise ValidationError("%s should be a number, got '%s'" %
                                  (self.fullname(), type(input)))
        
    def schema_details(self):
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
        return super(Number, self).schema_details(s)
_register_type(Number)


class Timestamp(Schema):
    _type = 'timestamp'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Timestamp._type, input, name, parent, **kwargs)
        _check_input(self.fullname(), input)

_register_type(Timestamp)


class TimestampHP(Schema):
    _type = 'timestamp-hp'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, TimestampHP._type, input, name, parent, **kwargs)
        _check_input(self.fullname(), input)

    def schema_details(self):
        return super(Number, self).schema_details('XXX Notes')
_register_type(TimestampHP)


class Object(Schema):
    _type = 'object'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Object._type, input, name, parent, **kwargs)
        self.props = OrderedDict()
        
        for prop,value in parse_prop(None, input, 'properties', {}).iteritems():
            c = Schema.parse(value, prop, self)
            self.props[prop] = c
            self.children.append(c)

        ap = parse_prop(None, input, 'additionalProperties')
        if type(ap) is bool:
            self.additionalProps = ap
        elif ap is not None:
            name = ap['id'] if ('id' in ap) else 'prop'
            c = Schema.parse(ap, '[' + name + ']', self)
            self.additionalProps = c
            self.children.append(c)
        else:
            self.additionalProps = None

        _check_input(self.fullname(), input)

    def __getitem__(self, name):
        if name in self.props:
            return self.props[name]

        return super(Object, self).__getitem__(name)
    
    def isSimple(self):
        return False
    
    def validate(self, input):
        if not isinstance(input, dict):
            raise ValidationError("%s should be an object, got '%s'" %
                                  (self.fullname(), type(input)))

        for k in input:
            if k in self.props:
                self.props[k].validate(input[k])
            elif self.additionalProps in (None, False):
                raise ValidationError("'%s' is not a valid property for %s" % (k, self.fullname()))
            elif isinstance (self.additionalProps, Schema):
                self.additionalProps.validate(input[k])
            
    def toxml(self, input, parent=None):
        if parent is not None:
            elem = ET.SubElement(parent, self.id)
        else:
            elem = ET.Element(self.id)
            
        subelems = OrderedDict()
        inline_props = OrderedDict()
        for k in input:
            if k not in self.props:
                if self.additionalProps is None:
                    raise ValueError('Invalid property: %s' % k)

                subobj = copy.copy(self.additionalProps)
                keyname = subobj.xmlKeyName or 'key'


                if subobj.isSimple():
                    subelem = ET.SubElement(elem, subobj.id)
                    subelem.set(keyname, k)

                    subelem.text = str(input[k])
                else:
                    subelem = subobj.toxml(input[k])
                    subelem.set(keyname, k)
                    elem.append(subelem)
                    
            else:
                prop = self.props[k]
                prop.toxml(input[k], elem)

        return elem
_register_type(Object)


class Array(Schema):
    _type = 'array'
    def __init__(self, input, name, parent, **kwargs):
        Schema.__init__(self, Array._type, input, name, parent, **kwargs)

        items = parse_prop(None, input, 'items', required=True)

        if 'id' in items:
            childname = items['id']
        else:
            childname = 'items'
        c = Schema.parse(items, childname, self)
        self.children.append(c)

        parse_prop(self, input, 'minItems')
        parse_prop(self, input, 'maxItems')

        _check_input(self.fullname(), input)

    def isSimple(self):
        return False
    
    @property
    def typestr(self):
        return 'array of <%s>' % self.children[0].typestr

    def __getitem__(self, name):
        try:
            num = int(name)
        except:
            if name != 'items':
                return super(Array, self).__getitem__(name)

        return self.children[0]
    
    def validate(self, input):
        if (type(input) is not list):
            raise ValidationError("%s should be an array, got '%s'" %
                                  (self.fullname(), type(input)))

        for o in input:
            self.children[0].validate(o)

    def toxml(self, input, parent=None):
        if parent is not None:
            elem = ET.SubElement(parent, '%s' % self.id)
        else:
            elem = ET.Element(self.id)
            
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

    def isSimple(self):
        return True
_register_type(Data)


class Relation(object):
    # Map of all known relations:
    #   schemas["<api>/schema#<fullid>/relations/<name>"] -> Schema
    relations = {}
    
    def __init__(self, input, name, schema):
        self.name = name
        self.schema = schema
        self.api = schema.api

        self.vars = None

        self._resource = None
        self._resource_name = parse_prop(None, input, 'resource', required=True)
        self.vars = parse_prop(self, input, 'vars')

        self.relations[self.fullid(api=True)] = self

        _check_input(self.fullname(), input)
        
    def __str__(self):
        return self.resource.name
        
    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__, self.fullid())

    @property
    def resource(self):
        if self._resource is None:
            self._resource = Schema.find_by_id(self.api, self._resource_name)
            if self._resource is None:
                raise KeyError("Invalid resource '%s' for relation: %s" % (self._resource_name, self.fullname()))
            
        return self._resource
    
    @classmethod
    def find_by_id(cls, api, id):
        """Find a relation by fullid."""

        for pre in ['', '/relations/']:
            fullid = '%s/schema#/%s%s' % (api, pre, id)
            if fullid in cls.relations:
                return cls.relations[fullid]

        return None

    def fullname(self):
        return self.schema.fullname() + '.relations.' + self.name
    
    def fullid(self, api=False):
        return self.schema.fullid(api) + '/relations/' + self.name
    
    def str_simple(self):
        return '%-30s %-20s %s\n' % (self.fullname(), '<relation>', self.description)

    def resolve(self, data, fragment=None, params=None):
        target_self = self.resource.links['self']
        target_request = target_self.request

        if params:
            vals = params
        else:
            vals = {}

        for var,relp in self.vars.iteritems():
            vals[var] = resolve_rel_pointer(data, fragment or '', relp)

        uri = target_self.path.resolve(vals)

        params = {}
        if target_request:
            for var,schema in target_request.props.iteritems():
                if var in vals:
                    schema.validate(vals[var])
                    params[var] = vals[var]
        
        return (uri, params)
       
class Link(object):
    # Map of all known links:
    #   schemas["<api>/schema#<fullid>/links/<name>"] -> Schema
    links = {}
    
    def __init__(self, input, name, schema):
        self.name = name
        self.schema = schema
        self.api = schema.api

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
                raise ParseError("Link '%s' defined with no path and schema has no 'self' link" %
                                 str(self))
            self.path = self.schema.links['self'].path
        else:
            self.path = None
            
        self._request = None
        if 'request' in input:
            self._request = Schema.parse(parse_prop(None, input, 'request'),
                                         parent=self, name='request')
        
        self._response = None
        if 'response' in input:
            self._response = Schema.parse(parse_prop(None, input, 'response'),
                                          parent=self, name='_response')


        self.links[self.fullid(api=True)] = self
    
        _check_input(self.fullname(), input)

    def __repr__(self):
        return "<jsonschema.%s '%s'>" % (self.__class__.__name__, self.fullid())
    
    @classmethod
    def find_by_id(cls, api, id):
        """Find a link by fullid."""

        for pre in ['', '/links/']:
            fullid = '%s/schema#/%s%s' % (api, pre, id)
            if fullid in cls.links:
                return cls.links[fullid]

        return None

    def fullname(self):
        return self.schema.fullname() + '.links.' + self.name
    
    def fullid(self, api=False):
        return self.schema.fullid(api) + '/links/' + self.name
    
    def str_simple(self):
        return '%-30s %-20s %s\n' % (self.fullname(), '<link>', self.description)

    @property
    def request(self):
        r =  self._request
        if type(r) is Ref:
            r = r.refschema
        return r
    
    @property
    def response(self):
        r =  self._response
        if type(r) is Ref:
            r = r.refschema
        return r
    

class Path(object):
    """The `Path` class manages URI templates and resolves variables for a schema.

    The `resolve` method supports resolving variables in the template from
    a data object conforming to the linked schema.

    When creating a path, the `pathdef` may take one of two forms:

      1) pathdef = '<uri-template>'

      2) pathdef = { 'template': '<uri-template'>,
                     'vars' : {
                        '<var1>' : <rel-json-pointer>,
                        '<var2>' : <rel-json-pointer>,
                        ... } }

    In both cases, the '<uri-template>' is follows RFC6570 syntax.  Variables
    in the template are resolved first looking to vars, then do the data object.

    Since URI templates can only specify simple variables, the second form is
    used as a level of indirection to move up or down in a data structure
    relative to the place where the link was defined.
    
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
        """Resolve all variables in this path template from `data` relative to `pointer`."""
        values = {}
        if data:
            values['$'] = resolve_pointer(data, pointer or '')

            if self.vars:
                for v in self.vars:
                    values[v] = resolve_rel_pointer(data, pointer or '', self.vars[v])

            if data and isinstance(data, dict):
                for v in data.keys():
                    if v not in values:
                        values[v] = data[v]

        tmpl = self.template
        logger.debug("%s template: %s" % (self.link.fullname(), tmpl))
        required = set(uritemplate.variables(self.template))
        have = set(values.keys())
        if not required.issubset(have):
            raise MissingParameter("Missing parameters for link '%s' path template '%s': %s" %
                                   (self.link.name, self.template, [x for x in required.difference(have)]))
            
        uri = uritemplate.expand(self.template, values)
        if uri[0] == '$':
            uri = self.link.api + uri[1:]
        return uri
