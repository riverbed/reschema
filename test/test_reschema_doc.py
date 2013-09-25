# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import coverage

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_SCHEMA = os.path.join(TEST_PATH, 'test_schema.yml')

cov = coverage.coverage()

cov.start()

import reschema
from reschema.html import *
from reschema.restschema import RestSchema
from reschema.tohtml import RestSchemaToHtml, ResourceToHtml, Options

rs = RestSchema()
rs.load(TEST_SCHEMA)

title = "%s v%s %s" % (rs.title, rs.version, rs.status)

outdir = 'reschema-doc-coverage'

if not os.path.exists(outdir):
    os.makedirs(outdir)
    

html = outdir + "/" + "test_schema.html"
if os.path.exists(html):
    os.remove(html)

htmldoc = reschema.html.Document(title, printable=False)
r2h = RestSchemaToHtml(rs, htmldoc.content, htmldoc.menu,
                       options=Options(printable=False,
                                       json=True, xml=True))
r2h.process()
htmldoc.write(html)

cov.stop()
cov.html_report(directory='reschema-doc-coverage')

print "Report written: ./reschema-doc-coverage/index.html"
