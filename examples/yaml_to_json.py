#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import sys
import json

from reschema.yaml_loader import marked_load

"""
Takes YAML input file and prints out a JSON representation to stdout.
"""


def convert(stream):
    yml = marked_load(stream)
    s = json.dumps(yml, indent=2).split("\n")
    result = []
    for line in s:
        result.append(line.rstrip())
    return '\n'.join(result)


if __name__ == '__main__':
    yaml_file = sys.argv[1]
    with open(yaml_file, 'r') as f:
        print convert(f)
