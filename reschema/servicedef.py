# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

# System imports
import os
import json
import urlparse
from cStringIO import StringIO
from collections import OrderedDict
import logging

from jsonpointer import resolve_pointer, JsonPointer

# Local imports
import reschema.jsonschema as jsonschema
from reschema.jsonschema import Schema
from reschema.util import parse_prop
from reschema import yaml_loader, json_loader
from reschema.exceptions import (ParseError, UnsupportedSchema,
                                 InvalidReference, DuplicateServiceId,
                                 InvalidServiceId, InvalidServiceName,
                                 NoContext)

__all__ = ['ServiceDef']


logger = logging.getLogger(__name__)


class ServiceDefLoadHook(object):
    """ Interface for load hooks.

    See ServiceDefCache.add_hook()

    """
    def find_by_id(self, id_):
        """ Find a ServiceDef by id.

        :param id_: the globally unique URI identifying a service
            definition.
        :return: a ServiceDef instance or None

        """
        raise NotImplemented()

    def find_by_name(self, name, version, provider):
        """ Find a ServiceDef by <name,version,provider> triplet.

        :param name: the service name
        :param version: the service version
        :param provider: the provide of the service
        :return: a ServiceDef instance or None

        """
        raise NotImplemented()


class ServiceDefCache(object):
    """ Manager for ServiceDef instances.

    A ServiceDefCache manages loading and finding ServiceDef
    instances by id as indicated in the 'id' property
    at the top level of the schema.

    This class is expected to be used as a singleton via the
    `instance()` class method.

    """

    # The singleton instance
    _instance = None

    # List of hooks to call in order to load schemas for as
    # yet unknown ids
    _load_hooks = []

    def __init__(self):
        # Ensure a duplicate instance is not created
        assert self._instance is None
        self.by_id = {}
        self.by_name = {}

    @classmethod
    def add_load_hook(cls, load_hook):
        """ Add a callable hook to load a schema by id.

        :param hook: an object that implements the ServiceDefLoadHook
            interface

        Hooks are processed in order until the first hook
        returns a ServiceDef instance.

        """
        cls._load_hooks.append(load_hook)

    @classmethod
    def instance(cls, *args, **kwargs):
        """ Return the global ServiceDefCache instance. """
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance

    @classmethod
    def clear(cls):
        """ Clear all known schemas. """
        logger.info("ServiceDefCache cleared")
        cls.instance().by_id = {}
        cls.instance().by_name = {}

    @classmethod
    def add(cls, servicedef):
        """ Add a new ServiceDef instance known at the given id. """
        self = cls.instance()
        logger.debug("%s add: %s" % (self, servicedef.id))
        sid = servicedef.id
        if sid in self.by_id:
            if self.by_id[sid] != servicedef:
                logger.debug("ids: %s" % (self.by_id.keys()))
                raise DuplicateServiceId(sid)
            return

        self.by_id[sid] = servicedef

        fullname = (servicedef.provider, servicedef.name, servicedef.version)
        self.by_name[fullname] = servicedef

        logger.info("ServiceDefCache: registered new schema: %s, %s" %
                    (fullname, sid))

    @classmethod
    def lookup_by_id(cls, id_):
        """ Resolve an id_ to a servicedef instance.

        If a service definition by this id is not yet in the cache, load
        hooks are invoked in order until one of them returns a instance.

        :raises InvalidServiceId: No schema found for id and could not
            be loaded

        """
        self = cls.instance()

        if id_ not in self.by_id:
            # Not found -- try loading via our hooks
            servicedef = None
            for hook in ServiceDefCache._load_hooks:
                servicedef = hook.find_by_id(id_)
            if servicedef is None:
                raise InvalidServiceId(
                    "Failed to load service definition: %s" % id_)

            self.add(servicedef)
        else:
            servicedef = self.by_id[id_]

        return servicedef

    @classmethod
    def lookup_by_name(cls, name, version, provider='riverbed'):
        """ Resolve <provider/name/version> triplet to a servicedef instance.

        If a service definition by this full name is not yet in the
        cache, load hooks are invoked in order until one of them
        returns a instance.

        :raises InvalidServiceId: No schema found for id and could not
            be loaded

        """
        self = cls.instance()

        fullname = (name, version, provider)
        if fullname not in self.by_name:
            # Not found -- try loading via our hooks
            servicedef = None
            for hook in ServiceDefCache._load_hooks:
                servicedef = hook.find_by_name(name, version, provider)
            if servicedef is None:
                raise InvalidServiceName(
                    "Failed to load service definition: %s/%s/%s" %
                    fullname)

            self.add(servicedef)
        else:
            servicedef = self.by_name[fullname]

        return servicedef

class ServiceDef(object):

    @classmethod
    def init_from_file(cls, filename):
        servicedef = ServiceDef()
        servicedef.load(filename)
        return servicedef

    def load(self, filename):
        """Loads and parses a JSON or YAML schema.

        Support both JSON(.json) and YAML(.yml/.yaml) file formats
        as detected by filename extensions.

        :param filename: The path to the JSON or YAML file.
        :raises ValueError: if the file has an unsupported extension.
        """
        # TODO: Add option for un-marked loads if performance becomes an issue

        with open(filename, 'r') as f:
            if filename.endswith('.json'):
                obj = json_loader.marked_load(f)
            elif filename.endswith(('.yml', '.yaml')):
                obj = yaml_loader.marked_load(f)
            else:
                raise ValueError(
                  "Unrecognized file extension, use '*.json' or '*.yaml': %s"
                  % filename)
        self.parse(obj)

    def parse_text(self, text, format='json'):
        """Loads and parses a schema from a string.

        :param text: The string containing the schema.
        :param format: Either 'json' (the default), 'yaml' or 'yml'.
                       This much match the format of the data in the string.
        """
        # TODO: Why not default format to 'yaml' as it will successfully
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

        self.schema = parse_prop(None, obj, '$schema', required=True)
        if self.schema != "http://support.riverbed.com/apis/service_def/2.1":
            raise UnsupportedSchema("Unsupported schema format: %s" %
                                    self.schema)

        parse_prop(self, obj, 'id', required=True)
        parsed_id = urlparse.urlparse(self.id)
        if not parsed_id.netloc:
            raise ParseError("Service definition 'id' property must be a "
                             "fully qualified URI: %s" % id)

        parse_prop(self, obj, 'provider', required=True)
        parse_prop(self, obj, 'name', required=True)
        parse_prop(self, obj, 'version', required=True)
        parse_prop(self, obj, 'title', self.name)
        parse_prop(self, obj, 'status', '')

        # 'description' is a doc property, supporting either:
        #    'description' : <string>
        #    'description' : { 'file': <filename>, 'format': <format> }
        #    'description' : { 'text': <string>, 'format': <format> }
        # where 'format' is optional and defaults to 'md'

        parse_prop(self, obj, 'description',
                   'Service Definition for ' + self.name)

        parse_prop(self, obj, 'documentationLink', '')
        parse_prop(self, obj, 'defaultAuthorization', None)

        self.types = OrderedDict()
        if 'types' in obj:
            for type_ in obj['types']:
                self.types[type_] = Schema.parse(obj['types'][type_],
                                                 name=type_,
                                                 id_prefix='/types',
                                                 servicedef=self)

        self.resources = OrderedDict()
        if 'resources' in obj:
            for resource in obj['resources']:
                input_ = obj['resources'][resource]
                sch = Schema.parse(input_,
                                   name=resource,
                                   id_prefix='/resources',
                                   servicedef=self)
                self.resources[resource] = sch

                if 'self' not in sch.links:
                    raise ParseError("Resource '%s' missing 'self' link" %
                                     resource, input_)
                if sch.links['self'].path is None:
                    raise ParseError(
                      "Resource '%s' 'self' link must define 'path'" %
                      resource, input_)

        parse_prop(self, obj, 'tasks', None)
        parse_prop(self, obj, 'request_headers', None)
        parse_prop(self, obj, 'response_headers', None)
        parse_prop(self, obj, 'errors', None)

        logger.debug("parsed %s, adding" % self.id)

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
        for r in self.resources:
            yield self.resources[r]

    def type_iter(self):
        for r in self.types:
            yield self.types[r]

    def find_resource(self, name):
        return self.resources[name]

    def find_type(self, name):
        return self.types[name]

    @classmethod
    def expand_id(cls, servicedef, reference):
        """ Expand a reference using this servicedef as a relative base

        Returns a fully qualified reference based.

        :param servicedef: a ServiceDef instance to use as context for
           relative names, may be None for absolute references

        :param reference: string reference to resolve

        The `reference` may be one of three supported forms:

           * `<server><path>#<fragment>` - fully qualified reference

           * `<path>#<fragment>` - reference is resolved against the
             same <server> as `servicedef`.  <path> starts with '/'

           * `#<fragment>` - reference is resolved against the same
             <server> and <path> as `servicedef`

        :raises NoContext: `reference` is relative but `servicedef` is
            not provided

        :raises InvalidReference: `reference` does not appear to
            be to the correct syntax

        """
        parsed_reference = urlparse.urlparse(reference)
        if parsed_reference.netloc:
            # Already a fully qualified address, let urlparse rejoin
            # to normalize it
            return parsed_reference.geturl()

        if servicedef is None:
            # relative references require a servicedef for context
            raise NoContext(reference)

        if reference[0] not in ['/', '#']:
            raise InvalidReference("relative references should "
                                   "start with '#' or '/'",
                                   reference)

        # urljoin will take care of the rest
        return urlparse.urljoin(servicedef.id, reference)

    @classmethod
    def find(cls, servicedef, reference):
        """ Resolve a reference using this servicedef as a relative base

        Returns a jsonschema.Schema instance

        :param servicedef: a ServiceDef instance to use as context for
           relative names, may be None for absolute references

        :param reference: string reference to resolve

        The `reference` may be one of three supported forms:

           * `<server><path>#<fragment>` - fully qualified reference

           * `<path>#<fragment>` - reference is resolved against the
             same <server> as `servicedef`.  <path> starts with '/'

           * `#<fragment>` - reference is resolved against the same
             <server> and <path> as `servicedef`

        :raises NoContext: `reference` is relative but `servicedef` is
            not provided

        :raises InvalidReference: `reference` does not appear to
            be to the correct syntax

        """

        parsed_reference = urlparse.urlparse(reference)
        if parsed_reference.netloc or parsed_reference.path:
            # More than just a fragment, expand the id and lookup the full
            # servicedef by id
            full_reference = cls.expand_id(servicedef, reference)
            reference_id = urlparse.urldefrag(full_reference)[0]
            servicedef = ServiceDefCache.lookup_by_id(reference_id)
        elif servicedef is None:
            # relative references require a servicedef for context
            raise NoContext(reference)

        # Now that we have a servicedef, look to the fragment for:
        #   '/resource/<resource_name>/...'
        #   '/types/<type_name>/...
        p = JsonPointer(parsed_reference.fragment)
        if p.parts[0] == 'resources':
            schema = servicedef.find_resource(p.parts[1])

        elif p.parts[0] == 'types':
            schema = servicedef.find_type(p.parts[1])

        else:
            raise InvalidReference("Expceted '/resources' or '/types'", reference)

        if len(p.parts) > 2:
            return schema.by_pointer('/' + '/'.join(p.parts[2:]))
        else:
            return schema
