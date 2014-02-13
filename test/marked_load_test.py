#!/usr/bin/env python

import os

import reschema
from reschema.exceptions import ReschemaException
from test_reschema import TEST_SCHEMA_YAML

TEST_SCHEMA_YAML_BAD = os.path.join(os.path.dirname(TEST_SCHEMA_YAML),
                                    'catalog_bad_property.yml')

"""
Exmaple script to demonstrate how marks can print out location
of parsing problems from source data.
"""

yaml_snippet_bad = """\
$schema: "service_def/2.0"
name: "Catalog"
version: "1.0"
title: "REST API for a book catalog"
servicePath: "/api/catalog/1.0"
defaultAuthorization: "required"
resources:
   info:
      type: object
      invalid_type: foo
      properties:
         owner: { type: string }
         email: { type: string }

      links:
         self: { path: "$/info" }
         books: { target: books }
         authors: { target: authors }
         get:
            method: GET
            response: { $ref: info }
         set:
            method: PUT
            request: { $ref: info }
            response: { $ref: info }
"""

json_snippet_bad = """\
{
  "$schema": "service_def/2.0",
  "name": "Catalog",
  "version": "1.0",
  "title": "REST API for a book catalog",
  "servicePath": "/api/catalog/1.0",
  "defaultAuthorization": "required",
  "resources": {
    "info": {
      "type": "object",
      "invalid_type": "foo",
      "properties": {
        "owner": {
          "type": "string"
        },
        "email": {
          "type": "string"
        }
      },
      "links": {
        "self": {
          "path": "$/info"
        },
        "books": {
          "target": "books"
        },
        "authors": {
          "target": "authors"
        },
        "get": {
          "method": "GET",
          "response": {
            "$ref": "info"
          }
        },
        "set": {
          "method": "PUT",
          "request": {
            "$ref": "info"
          },
          "response": {
            "$ref": "info"
          }
        }
      }
    }
  }
}
"""

print ''
print 'Parsing bad YAML ...'
print '-' * 80
try:
    r = reschema.ServiceDef()
    r.parse_text(yaml_snippet_bad, format='yaml')
except ReschemaException as e:
    print e

print ''
print 'Parsing bad YAML from File ...'
print '-' * 80
try:
    r = reschema.ServiceDef()
    print "TEST_SCHEMA_YAML: %s" % TEST_SCHEMA_YAML
    r.load(TEST_SCHEMA_YAML)
except ReschemaException as e:
    print e

print ''
print 'Parsing bad JSON ...'
print '-' * 80
try:
    r = reschema.ServiceDef()
    r.parse_text(json_snippet_bad)
except ReschemaException as e:
    print e

print ''
print 'Validating good YAML with bad values ...'
print '-' * 80
try:
    r = reschema.ServiceDef()
    r.load(TEST_SCHEMA_YAML)
    a = r.resources['test_string']
    a.validate(42)
except ReschemaException as e:
    print e

#print ''
#print 'Validating good JSON with bad values ...'
#print '-' * 80
#try:
#    r = reschema.ServiceDef()
#    r.load(TEST_SCHEMA_JSON)
#    a = r.resources['test_string']
#    a.validate(42)
#except ReschemaException as e:
#    print e
