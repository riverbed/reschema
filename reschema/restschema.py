# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

# System imports
import os
import json
from cStringIO import StringIO
from collections import OrderedDict

from jsonpointer import resolve_pointer, JsonPointer

# Local imports
from reschema.jsonschema import Schema
from reschema.util import parse_prop
from reschema import yaml_loader, json_loader
from reschema.exceptions import ParseError

__all__ = ['RestSchema']


class RestSchema(object):

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

        parse_prop(self, obj, 'restSchemaVersion', required=True)
        parse_prop(self, obj, 'name', required=True)
        parse_prop(self, obj, 'version', required=True)
        parse_prop(self, obj, 'title', self.name)
        parse_prop(self, obj, 'status', '')

        # 'description' is a doc property, supporting either:
        #    'description' : <string>
        #    'description' : { 'file': <filename>, 'format': <format> }
        #    'description' : { 'text': <string>, 'format': <format> }
        # where 'format' is optional and defaults to 'md'

        parse_prop(self, obj, 'description', 'REST Schema for ' + self.name)
            
        parse_prop(self, obj, 'documentationLink', '')
        parse_prop(self, obj, 'servicePath', '')
        parse_prop(self, obj, 'defaultAuthorization', None)

        self.types = OrderedDict()
        if 'types' in obj:
            for type_ in obj['types']:
                self.types[type_] = Schema.parse(
                  obj['types'][type_],
                  name=type_,
                  api=self.servicePath)
        
        self.resources = OrderedDict()
        if 'resources' in obj:
            for resource in obj['resources']:
                input_ = obj['resources'][resource]
                sch = Schema.parse(input_, name=resource, api=self.servicePath)
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

    def resource_iter(self):
        for r in self.resources:
            yield self.resources[r]

    def find_resource(self, name):
        return self.resources[name]

    def find_type(self, name):
        return self.types[name]

    def find(self, name):
        if name[0] == '/':
            p = JsonPointer(name)
            parts = p.parts
            if parts[0] in self.resources:
                o = self.resources[parts[0]]
                return o.by_pointer('/' + '/'.join(parts[1:]))
        elif name in self.resources:
            return self.resources[name]
        else:
            raise KeyError("%s has no such resource: %s" % (self, name))
