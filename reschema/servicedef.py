# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
The `ServiceDef` class represents a single service definition as a
collection of resources and types.  An instance of this class is
normally created by parsing a service definition file.

Manual ServiceDef creation
--------------------------

An instance may be created directly froma file:

.. code-block:: python

   >>> bookstore_def = ServiceDef.create_from_file('bookstore.yaml')

This is useful for simple stand alone services.  Once created, the
services' resources and types may be browsed the object used for
validation:

.. code-block:: python

   # Get the 'author' resource
   >>> author_res = bookstore_def.resources['author']

   # Define an author and validate that the format is correct
   >>> author = dict(id=5, name='John Doe')
   >>> author_res.validate(author)

   # If the format is incorrect, a ValidationError is thrown
   >>> author = dict(id='5', name='John Doe')
   >>> author_res.validate(author)

   ValidationError: ("author.id should be a number, got '<type 'str'>'", <servicedef.Integer 'http://support.riverbed.com/apis/bookstore/1.0#/resources/author/properties/id'>)

Using Managers
--------------

For larger projects that span multiple services, a ServiceDefManager can
be used to load service defintions on demand.  This is particularly important
when one service defintion references types or resources from another
service definition.

.. code-block:: python

   # Create a ServiceDefManager to manage service definitions The
   # CustomServiceDefLoader implements the ServiceDefLoadHook andmust
   # be defined in order to load service definitions on this system.
   >>> svcdef_mgr = ServiceDefManager()
   >>> svcdef_mgr.add_load_hook(CustomServiceDefLoader)

   # Load a service by looking for it by name/version
   >>> bookstore_def = svcdef_mgr.find_by_name('bookstore', '1.0')

"""

# System imports
import urlparse
import json
from cStringIO import StringIO
from collections import OrderedDict
import logging
import traceback

from jsonpointer import JsonPointer

# Local imports
import reschema.jsonschema as jsonschema
from reschema.jsonschema import Schema
from reschema.parser import Parser
from reschema import yaml_loader, json_loader
from reschema.exceptions import (ParseError, UnsupportedSchema, NoManager,
                                 InvalidReference, DuplicateServiceId,
                                 InvalidServiceId, InvalidServiceName,
                                 ReschemaLoadHookException)
import reschema.settings

__all__ = ['ServiceDef']
logger = logging.getLogger(__name__)


SUPPORTED_SCHEMAS = frozenset([
    "http://support.riverbed.com/apis/service_def/2.2",
])
""" The set of schema versions understood by this version of reschema """


class ServiceDefLoadHook(object):
    """ Interface for load hooks.

    See ServiceDefManager.add_hook()

    """
    def find_by_id(self, id_):
        """ Find a ServiceDef by id.

        :param id_: the globally unique URI identifying a service
            definition.
        :return: a ServiceDef instance or None

        """
        raise NotImplementedError()

    def find_by_name(self, name, version, provider):
        """ Find a ServiceDef by <name,version,provider> triplet.

        :param name: the service name
        :param version: the service version
        :param provider: the provider of the service
        :return: a ServiceDef instance or None

        """
        raise NotImplementedError()


class ServiceDefManager(object):
    """ Manager for ServiceDef instances.

    A ServiceDefManager manages loading and finding ServiceDef
    instances by id as indicated in the 'id' property
    at the top level of the schema.

    """

    def __init__(self):
        self.by_id = {}
        self.by_name = {}

        # List of hooks to call in order to load schemas for as
        # yet unknown ids
        self._load_hooks = []

    def add_load_hook(self, load_hook):
        """ Add a callable hook to load a schema by id.

        :param hook: an object that implements the ServiceDefLoadHook
            interface

        Hooks are processed in order until the first hook
        returns a ServiceDef instance.

        """
        self._load_hooks.append(load_hook)

    def clear(self):
        """ Clear all known schemas. """
        logger.info("ServiceDefManager cleared")
        self.by_id = {}
        self.by_name = {}

    def add(self, servicedef):
        """ Add a new ServiceDef instance known at the given id. """
        logger.debug("%s add: %s" % (self, servicedef.id))
        sid = servicedef.id
        if sid in self.by_id:
            if self.by_id[sid] != servicedef:
                logger.debug("ids: %s" % (self.by_id.keys()))
                raise DuplicateServiceId(sid)
            return

        self.by_id[sid] = servicedef

        fullname = (servicedef.name, servicedef.version, servicedef.provider)
        self.by_name[fullname] = servicedef

        logger.info("ServiceDefManager: registered new schema: %s, %s" %
                    (fullname, sid))
        servicedef.manager = self

    def find_by_id(self, id_):
        """ Resolve an id_ to a servicedef instance.

        If a service definition by this id is not yet in the cache, load
        hooks are invoked in order until one of them returns a instance.

        :raises InvalidServiceId: No schema found for id and could not
            be loaded

        """
        if id_ not in self.by_id:
            # Not found -- try loading via our hooks
            servicedef = None
            for hook in self._load_hooks:
                try:
                    servicedef = hook.find_by_id(id_)
                except:
                    tb = traceback.format_exc()
                    raise ReschemaLoadHookException(tb)
                if servicedef:
                    break
            if servicedef is None:
                raise InvalidServiceId(
                    "Failed to load service definition: %s" % id_)
            self.add(servicedef)
        else:
            servicedef = self.by_id[id_]

        return servicedef

    def find_by_name(self, name, version, provider='riverbed'):
        """ Resolve <provider/name/version> triplet to a servicedef instance.

        If a service definition by this full name is not yet in the
        cache, load hooks are invoked in order until one of them
        returns a instance.

        :param name: the service name
        :param version: the service version
        :param provider: the provider of the service
        :return: a ServiceDef instance

        :raises InvalidServiceId: No schema found for id and could not
            be loaded

        """
        fullname = (name, version, provider)
        if fullname not in self.by_name:
            # Not found -- try loading via our hooks
            servicedef = None
            for hook in self._load_hooks:
                try:
                    servicedef = hook.find_by_name(name, version, provider)
                except:
                    tb = traceback.format_exc()
                    raise ReschemaLoadHookException(tb)
                if servicedef:
                    break
            if servicedef is None:
                raise InvalidServiceName(
                    "Failed to load service definition: %s/%s/%s" %
                    fullname)

            self.add(servicedef)
        else:
            servicedef = self.by_name[fullname]

        return servicedef


class ServiceDef(object):
    """ Loads and represents the complete service definition

    A ServiceDef parses the top-level service definition fields and
    calls `reschema.schema.Schema.parse()` on sub-sections that
    have JSON Schema-based values.

    :param manager: The ServiceManager, if any, that is keeping track
        of this particular service definition.
    """

    def __init__(self, manager=None):
        self.manager = manager

    @classmethod
    def create_from_file(cls, filename, **kwargs):
        servicedef = ServiceDef(**kwargs)
        servicedef.load(filename)
        return servicedef

    @classmethod
    def create_from_text(cls, text, format='json', **kwargs):
        servicedef = ServiceDef(**kwargs)
        servicedef.parse_text(text, format=format)
        return servicedef

    def load(self, filename):
        """Loads and parses a JSON or YAML schema.

        Support both JSON(.json) and YAML(.yml/.yaml) file formats
        as detected by filename extensions.

        :param filename: The path to the JSON or YAML file.
        :raises ValueError: if the file has an unsupported extension.
        """

        if filename.endswith('.json'):
            format = 'json'

        elif filename.endswith(('.yml', '.yaml')):
            format = 'yaml'

        else:
            raise ValueError(
                "Unrecognized file extension, use '*.json' or '*.yaml': %s"
                % filename)

        with open(filename, 'r') as f:
            return self.load_from_stream(f, format=format)

    def load_from_stream(self, f, format='yaml'):
        """Loads and parses a JSON or YAML schema.

        Support both JSON(.json) and YAML(.yml/.yaml) file formats
        as detected by filename extensions.

        :param f: An open file object.
        :raises ValueError: if the file has an unsupported extension.
        """

        if format == 'json':
            if reschema.settings.MARKED_LOAD:
                obj = json_loader.marked_load(f)
            else:
                obj = json.load(f, object_pairs_hook=OrderedDict)

        elif format == 'yaml':
            if reschema.settings.MARKED_LOAD:
                obj = yaml_loader.marked_load(f)
            else:
                obj = yaml_loader.ordered_load(f)

        else:
            raise ValueError(
                "Unrecognized format, use 'json' or 'yaml': %s" % format)

        self.parse(obj)

    def parse_text(self, text, format='yaml'):
        """Loads and parses a schema from a string.

        :param text: The string containing the schema.
        :param format: Either 'json' (the default), 'yaml' or 'yml'.
                       This much match the format of the data in the string.
        """

        stream = StringIO(text)
        if format == 'json':
            obj = json_loader.marked_load(stream)
        elif format == 'yaml' or format == 'yml':
            obj = yaml_loader.marked_load(stream)

        return self.parse(obj)

    def parse(self, obj):
        """Parses a Python data object representing a schema.

        :param obj: The Python object containig the schema data.
        :type obj: dict
        """
        # Common properties

        with Parser(obj, '<servicdef>', self) as parser:
            parser.parse('$schema', required=True, save_as='schema')
            if self.schema not in SUPPORTED_SCHEMAS:
                raise UnsupportedSchema("Unsupported schema format: %s" %
                                        self.schema)

            parser.parse('id', required=True)
            parsed_id = urlparse.urlparse(self.id)
            if not parsed_id.netloc:
                raise ParseError("Service definition 'id' property must be a "
                                 "fully qualified URI: %s" % id)

            # Preform some preprocessing:
            #  - Expand all relative $ref targets to full absoslute references
            parser.preprocess_input(self.id)

            parser.parse('provider', required=True)
            parser.parse('name', required=True)
            parser.parse('version', required=True, types=[str, unicode])
            parser.parse('title', '')
            parser.parse('status', '')

            # 'description' is a doc property, supporting either:
            #    'description' : <string>
            #    'description' : { 'file': <filename>, 'format': <format> }
            #    'description' : { 'text': <string>, 'format': <format> }
            # where 'format' is optional and defaults to 'md'

            parser.parse('description', '')

            parser.parse('documentationLink', '')
            parser.parse('defaultAuthorization')

            self.types = OrderedDict()
            for type_ in parser.parse('types', [], save=False):
                self.types[type_] = Schema.parse(obj['types'][type_],
                                                 name=type_,
                                                 id='#/types/%s' % type_,
                                                 servicedef=self)

            self.resources = OrderedDict()
            for resource in parser.parse('resources', [], save=False):
                input_ = obj['resources'][resource]
                sch = Schema.parse(input_,
                                   name=resource,
                                   id='#/resources/%s' % resource,
                                   servicedef=self)
                self.resources[resource] = sch

            parser.parse('tasks')
            parser.parse('request_headers')
            parser.parse('response_headers')
            parser.parse('errors')
            parser.parse('tags', {}, types=dict)

    def check_references(self):
        """ Iterate through all schemas and check references.

        Check all resources and types associated with this service
        defintion and verify that all references can be properly
        resolved.  This returns an array of jsonschema.Ref instances
        that cannot be resolved.

        """

        def _check(r):

            if type(r) is jsonschema.Ref:
                try:
                    # Simply access r.refschema which will cause
                    # the refence to be checked
                    r.refschema
                except InvalidReference:
                    errors.append(r)
            else:
                for c in r.children:
                    _check(c)

        errors = []

        for r in self.resource_iter():
            _check(r)

        for r in self.type_iter():
            _check(r)

        return errors

    def resource_iter(self):
        """ Generator for iterating over all resources """
        for r in self.resources:
            yield self.resources[r]

    def type_iter(self):
        """ Generator for iterating over all types """
        for r in self.types:
            yield self.types[r]

    def find_resource(self, name):
        """ Look up and return a resource by name """
        return self.resources.get(name, None)

    def find_type(self, name):
        """ Look up and return a type by name """
        return self.types.get(name, None)

    def find(self, reference):
        """ Resolve a reference using this servicedef as a relative base

        Returns a jsonschema.Schema instance

        :param reference: string reference to resolve

        The `reference` may be one of three supported forms:

           * `<server><path>#<fragment>` - fully qualified reference

           * `<path>#<fragment>` - reference is resolved against the
             same <server> as `servicedef`.  <path> starts with '/'

           * `#<fragment>` - reference is resolved against the same
             <server> and <path> as `servicedef`

        :raises InvalidReference: `reference` does not appear to
            be to the correct syntax

        """

        parsed_reference = urlparse.urlparse(reference)
        if parsed_reference.netloc or parsed_reference.path:
            # More than just a fragment, expand the id and find the full
            # servicedef by id
            full_reference = Parser.expand_ref(self.id, reference)
            reference_id = urlparse.urldefrag(full_reference)[0]

            if reference_id == self.id:
                servicedef = self
            else:
                if self.manager is None:
                    raise NoManager(reference)
                servicedef = self.manager.find_by_id(reference_id)
        else:
            servicedef = self

        # Now that we have a servicedef, look to the fragment for:
        #   '/resource/<resource_name>/...'
        #   '/types/<type_name>/...
        p = JsonPointer(parsed_reference.fragment)
        if p.parts[0] == 'resources':
            schema = servicedef.find_resource(p.parts[1])

        elif p.parts[0] == 'types':
            schema = servicedef.find_type(p.parts[1])

        else:
            raise InvalidReference("Expected '/resources' or '/types'",
                                   reference)

        if len(p.parts) > 2 and schema is not None:
            return schema.by_pointer('/' + '/'.join(p.parts[2:]))
        else:
            return schema
