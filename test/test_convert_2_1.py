# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import logging
import unittest
import subprocess

from reschema.exceptions import UnsupportedSchema
from reschema import ServiceDef

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_21 = os.path.join(TEST_PATH, 'service_convert_2.1.yaml')
SERVICE_22 = os.path.join(TEST_PATH, 'service_convert_2.2.yaml')

PACKAGE_PATH = os.path.dirname(TEST_PATH)

CONVERT_21_22 = os.path.join(PACKAGE_PATH, 'bin', 'convert-2.1-2.2')


class TestConvert21(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_schema_21(self):
        s = ServiceDef()
        with self.assertRaises(UnsupportedSchema):
            s.load(SERVICE_21)

    def test_convert_21_22(self):
        if os.path.exists(SERVICE_22):
            os.unlink(SERVICE_22)

        try:
            subprocess.check_output([CONVERT_21_22, '-f', SERVICE_21,
                                     '-o', SERVICE_22])
            s = ServiceDef()
            s.load(SERVICE_22)

            t = s.find('#/types/type3')
            t.validate({'key1': 15})

        finally:
            if os.path.exists(SERVICE_22):
                os.unlink(SERVICE_22)


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.INFO)
    unittest.main()
