# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import unittest

from reschema.exceptions import ReschemaException
from reschema import ServiceDef, ServiceDefManager

"""
Exmaple script to demonstrate how marks can print out location
of parsing problems from source data.
"""

yaml_snippet_bad = """\
$schema: "service_def/2.0"
name: "Bookstore"
version: "1.0"
title: "REST API for a bookstore"
servicePath: "/api/bookstore/1.0"
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
  "name": "Bookstore",
  "version": "1.0",
  "title": "REST API for a bookstore",
  "servicePath": "/api/bookstore/1.0",
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


class TestMarkedLoad(unittest.TestCase):

    def test_bad_yaml(self):
        with self.assertRaises(ReschemaException):
            r = ServiceDef()
            r.parse_text(yaml_snippet_bad, format='yaml')

    def test_bad_json(self):
        with self.assertRaises(ReschemaException):
            r = ServiceDef()
            r.parse_text(json_snippet_bad)
