#!/usr/bin/env python

import sys
import json

from reschema.yaml_loader import marked_load

"""
Takes YAML input file and prints out a JSON representation to stdout.
"""


def convert(stream):
    yml = marked_load(stream)
    return json.dumps(yml, indent=2)


if __name__ == '__main__':
    yaml_file = sys.argv[1]
    with open(yaml_file, 'r') as f:
        print convert(f)
