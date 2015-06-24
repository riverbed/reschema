# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import pip
import sys

from setuptools.command.test import test as TestCommand
from gitpy_versioning import get_version

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = open('README.rst').read()

doc = [
    'sphinx',
]

test = [
    'pytest',
    'mock',
]

setup(
    name='reschema',
    version=get_version(),
    description=("reschema - Parse REST API service defintions into Python "
                 "objects, support documentation generation"),
    long_description=readme,
    author="Riverbed Technology",
    author_email="cwhite@riverbed.com",
    packages=[
        'reschema',
    ],
    package_dir={'reschema': 'reschema'},
    scripts=[
        'bin/reschema-doc',
        'bin/relint'
    ],
    include_package_data=True,
    install_requires=[
        'PyYAML',
        'Markdown',
        'uritemplate',
        'jsonpointer',
    ],
    extras_require={
        'test': test,
        'doc': doc,
        'dev': test + doc,
        'all': [],
    },
    tests_require=test,
    url="https://gitlab.lab.nbttech.com/steelscript/reschema/",
    keywords='reschema',
)
