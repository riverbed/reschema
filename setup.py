import os
import pip
import sys

from setuptools.command.test import test as TestCommand
from pip.req import parse_requirements
from versioning import get_version

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def requirements():
    return [str(ir.req) for ir in parse_requirements('requirements.txt')]

readme = open('README.rst').read()

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
    install_requires=requirements(),
    keywords='reschema',
    tests_require=['pytest', 'mock'],
)
