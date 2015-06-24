# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os

#
# Set to True to load all description fields associated with
# a JSON schema.  If false (default), the descriptions will be blank
#
LOAD_DESCRIPTIONS = ('RESCHEMA_LOAD_DESCRIPTIONS' in os.environ)

#
# Set to True to add file / line numbers while loading schema
# files.  Useful when debugging yaml/json file syntax errors
# Defaults to False
#
MARKED_LOAD = ('RESCHEMA_MARKED_LOAD' in os.environ)

#
# Set to True for verbose debugging
#
VERBOSE_DEBUG = ('RESCHEMA_VERBOSE_DEBUG' in os.environ)
