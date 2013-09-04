# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

# System imports
import os
import json
import yaml
from collections import OrderedDict
from StringIO import StringIO
from jsonpointer import resolve_pointer, JsonPointer

# Local imports
import reschema.yaml_omap # This must be loaded before calling yaml.load()
from reschema.jsonschema import Schema
from reschema.util import parse_prop
import reschema.yaml_omap

__all__ = ['RestSchema']


class RestSchema(object):

    def __init__(self):
        self.filename = None
        self.dir = None
        
    def load(self, filename):
        self.filename = filename
        self.dir = os.path.dirname(os.path.abspath(filename))

        # Support both JSON(.json) and YAML(.yml) file formats
        with open(filename, 'r') as f:
            if filename.endswith('.json'):
                obj = json.load(f, object_pairs_hook=OrderedDict)
            elif filename.endswith('.yml'):
                obj = yaml.load(f)
            else:
                raise ValueError("Unrecognized file extension, use '*.json' or '*.yml': %s"
                                 % filename)

        self.parse(obj)

    def parse_text(self, text, format='json'):
        if format == 'json':
            obj = json.loads(text, object_pairs_hook=OrderedDict)
        elif format == 'yaml' or format == 'yml':
            obj = yaml.load(StringIO(text))

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
            return self.resource[name]
        else:
            raise KeyError("%s has no such resource: %s" % (self, name))
        
        
