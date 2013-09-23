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

__all__ = ['RestSchema']


class RestSchema(object):

    def __init__(self):
        self.filename = None
        self.dir = None

    def load(self, filename):
        self.filename = filename
        self.dir = os.path.dirname(os.path.abspath(filename))

        # Support both JSON(.json) and YAML(.yml/.yaml) file formats
        # TODO: Add option for un-marked loads if performance becomes an issue

        with open(filename, 'r') as f:
            if filename.endswith('.json'):
                obj = json_loader.marked_load(f)
            elif filename.endswith(('.yml', '.yaml')):
                obj = yaml_loader.marked_load(f)
            else:
                raise ValueError("Unrecognized file extension, use '*.json' or '*.yaml': %s"
                                 % filename)
        self.parse(obj)

    def parse_text(self, text, format='json'):
        stream = StringIO(text)
        if format == 'json':
            obj = json_loader.marked_load(stream)
        elif format == 'yaml' or format == 'yml':
            obj = yaml_loader.marked_load(stream)

        return self.parse(obj)

    def parse(self, obj):
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

        if 'types' in obj:
            self.types = OrderedDict()
            for type_ in obj['types']:
                self.types[type_] = Schema.parse(obj['types'][type_],
                                                 name=type_, api=self.servicePath)
        
        if 'resources' in obj:
            self.resources = OrderedDict()
            for resource in obj['resources']:
                self.resources[resource] = Schema.parse(obj['resources'][resource],
                                                        name=resource, api=self.servicePath)

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
                return o['/' + '/'.join(parts[1:])]
        elif name in self.resources:
            return self.resources[name]
        else:
            raise KeyError("%s has no such resource: %s" % (self, name))
