# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

# System imports
import urlparse
from cStringIO import StringIO
from collections import OrderedDict
import logging

from jsonpointer import JsonPointer

# Local imports
import reschema.jsonschema as jsonschema
from reschema.jsonschema import Schema
from reschema.util import parse_prop
from reschema import yaml_loader, json_loader
from reschema.exceptions import (ParseError, UnsupportedSchema, NoManager,
                                 InvalidReference, DuplicateServiceId,
                                 InvalidServiceId, InvalidServiceName)

__all__ = ['ServiceDef']


logger = logging.getLogger(__name__)


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
                servicedef = hook.find_by_id(id_)
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
                servicedef = hook.find_by_name(name, version, provider)
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
        parse_prop(self, obj, 'version', required=True,
                   valid_type=[str, unicode])
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
                                                 id='#/types/%s' % type_,
                                                 servicedef=self)

        self.resources = OrderedDict()
        if 'resources' in obj:
            for resource in obj['resources']:
                input_ = obj['resources'][resource]
                sch = Schema.parse(input_,
                                   name=resource,
                                   id='#/resources/%s' % resource,
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

    def expand_id(self, reference):
        """ Expand a reference using this servicedef as a relative base

        Returns a fully qualified reference based.

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
        if parsed_reference.netloc:
            # Already a fully qualified address, let urlparse rejoin
            # to normalize it
            return parsed_reference.geturl()

        if reference[0] not in ['/', '#']:
            raise InvalidReference("relative references should "
                                   "start with '#' or '/'",
                                   reference)

        # urljoin will take care of the rest
        return urlparse.urljoin(self.id, reference)

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
            full_reference = self.expand_id(reference)
            reference_id = urlparse.urldefrag(full_reference)[0]
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

        if len(p.parts) > 2:
            return schema.by_pointer('/' + '/'.join(p.parts[2:]))
        else:
            return schema
