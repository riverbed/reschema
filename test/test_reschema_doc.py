# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from __future__ import print_function

import os
import unittest
import shutil
import logging

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yml')
SERVICE_DEF_CATALOG = os.path.join(TEST_PATH, '../examples/Catalog.yml')

outdir = 'test_reschema_doc_output'
if os.path.exists(outdir):
    shutil.rmtree(outdir)

os.makedirs(outdir)

import reschema
from reschema.html import *
from reschema import ServiceDef
from reschema.tohtml import ServiceDefToHtml, Options
from reschema.doc import ReschemaDoc, ReschemaDocException


def process_file(filename):
    r = ReschemaDoc()
    r.parse_args(['-f', filename,
                  '--outdir', outdir,
                  '--html',
                  ])
    r.run()
    return


class TestReschema(unittest.TestCase):

    def test_service(self):
        process_file(SERVICE_DEF_TEST)

    def test_service_ref(self):
        process_file(SERVICE_DEF_TEST_REF)

    def test_service_catalog(self):
        process_file(SERVICE_DEF_CATALOG)


if __name__ == '__main__':
    for filename in [SERVICE_DEF_TEST,
                     SERVICE_DEF_TEST_REF,
                     SERVICE_DEF_CATALOG]:
        html = process_file(filename)
