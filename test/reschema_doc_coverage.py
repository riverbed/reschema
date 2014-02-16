# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from __future__ import print_function

import os
import coverage

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_SCHEMA = os.path.join(TEST_PATH, 'test_schema.yml')
CATALOG_SCHEMA = os.path.join(TEST_PATH, '../examples/Catalog.yml')

cov = coverage.coverage()

cov.start()

import reschema
from reschema.html import *
from reschema import ServiceDef
from reschema.tohtml import ServiceDefToHtml, Options

for filename in [TEST_SCHEMA, CATALOG_SCHEMA]:
    rs = ServiceDef()
    rs.load(filename)

    title = "%s v%s %s" % (rs.title, rs.version, rs.status)

    outdir = 'reschema_doc_coverage_output'

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    base = os.path.splitext(os.path.basename(filename))[0]

    html = "%s/%s.html" % (outdir, base)
    if os.path.exists(html):
        os.remove(html)

    htmldoc = reschema.html.Document(title, printable=False)
    r2h = ServiceDefToHtml(rs, htmldoc.content, htmldoc.menu,
                           root='/api',
                           options=Options(printable=False,
                                           json=True, xml=True))
    r2h.process()
    htmldoc.write(html)
    print("HTML output: ./%s" % html)

cov.stop()
cov.html_report(directory=outdir)

print("Report written: ./%s/index.html" % outdir)
