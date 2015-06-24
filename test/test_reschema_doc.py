# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import print_function

import os
import unittest
import shutil
import logging
from reschema.util import str_to_id as html_str_to_id

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yaml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yaml')
SERVICE_DEF_BOOKSTORE = os.path.join(TEST_PATH, '../examples/bookstore.yaml')
SERVICE_DEF_INVALID_REF = os.path.join(TEST_PATH,
                                       'service_test_invalid_ref.yaml')

outdir = 'test_reschema_doc_output'
if os.path.exists(outdir):
    shutil.rmtree(outdir)

os.makedirs(outdir)

import reschema
from reschema import ServiceDef
from reschema.tohtml import ResourceToHtml, RefSchemaProxy
from reschema.doc import ReschemaDoc


def process_file(filename, *args):
    r = ReschemaDoc()
    rargs = ['-f', filename,
             '--outdir', outdir,
             '--html']

    for arg in args:
        rargs.extend(['-r', arg])

    r.parse_args(rargs)
    r.run()
    return


class TestReschema(unittest.TestCase):

    def test_service(self):
        process_file(SERVICE_DEF_TEST)

    def test_service_ref(self):
        process_file(SERVICE_DEF_TEST_REF, SERVICE_DEF_TEST)

    def test_service_bookstore(self):
        process_file(SERVICE_DEF_BOOKSTORE)


class TestReschemaInvalidRef(unittest.TestCase):

    def setUp(self):
        self.sd = ServiceDef()
        self.sd.load(SERVICE_DEF_INVALID_REF)

    def test_invalid_ref_in_property(self):
        """
        testing when one property's ref consists of undefined types,
        an invalid reference exception should be raised, such as below:
        properties:
           property: { $ref: '#/types/blah' }
        """
        with self.assertRaises(reschema.exceptions.InvalidReference):
            schema = self.sd.resources.values()[0].properties['name']
            RefSchemaProxy(schema, None)

    def test_invalid_ref_in_links(self):
        """
        testing when one property's ref consists of undefined resources,
        an invalid reference exception should be raised. such as below:
        properties:
        links:
          self: { path: '$/test_invalid_ref_in_lnks'}
          params:
             id:
                $ref: '#/types/does_not_exist'
        """
        with self.assertRaises(reschema.exceptions.InvalidReference):
            resource = self.sd.resources.values()[0]
            title = "%s v%s %s" % (self.sd.title, self.sd.version,
                                   self.sd.status)
            htmldoc = reschema.html.Document(title, printable=False)
            r2h = ResourceToHtml(resource, htmldoc.content,
                                 htmldoc.menu.add_submenu(),
                                 "http://{device}/{root}",
                                 None)
            baseid = html_str_to_id(r2h.schema.fullid(True))
            div = r2h.container.div(id=baseid)
            r2h.menu.add_item(r2h.schema.name, href=div)
            r2h.process_links(div, baseid)


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
