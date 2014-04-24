# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.
from __future__ import print_function

import sys
import os
import imp
import logging
import unittest

import reschema
import reschema.lint

logger = logging.getLogger(__name__)

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
SERVICE_DEF_TEST = os.path.join(TEST_PATH, 'service_test.yml')
SERVICE_DEF_TEST_REF = os.path.join(TEST_PATH, 'service_test_ref.yml')


class TestLint(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_lint(self):
        r = reschema.ServiceDef()
        r.load(SERVICE_DEF_TEST)
        reschema.lint.lint(r)


class TestRelint(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_relint(self):
        # load the relint script as a module
        path = os.path.realpath(os.path.join(TEST_PATH, '..', 'bin', 'relint'))
        module = imp.load_source('relint', path)

        # grab the 'start' function, which is relint's version of main()
        start = getattr(module, 'start')

        # set up argv
        sys.argv = [sys.argv[0], SERVICE_DEF_TEST]

        failures = start()


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    unittest.main()
