#!/usr/bin/env python

import reschema
from reschema.exceptions import ReschemaException
from test_reschema import TEST_SCHEMA_JSON, TEST_SCHEMA_YAML


"""
Exmaple script to demonstrate how marks can print out location
of parsing problems from source data.
"""

yaml_snippet_bad = """\
restSchemaVersion: "2.0"
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
  "restSchemaVersion": "2.0",
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

try:
    r = reschema.RestSchema()
    print ''
    print 'Parsing bad YAML ...'
    r.parse_text(yaml_snippet_bad, format='yaml')
except ReschemaException as e:
    print e

try:
    r = reschema.RestSchema()
    print ''
    print 'Parsing bad JSON ...'
    r.parse_text(json_snippet_bad)
except ReschemaException as e:
    print e

try:
    r = reschema.RestSchema()
    r.load(TEST_SCHEMA_JSON)
    a = r.resources['author'].props['name']
    a.validate(42)
except ReschemaException as e:
    print e


