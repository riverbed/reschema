# Copyright (c) 2019 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import sys

from gitpy_versioning import get_version


from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


readme = open('README.rst').read()

doc = [
    'sphinx',
]

install_requires = [
    'PyYAML',
    'Markdown',
    'uritemplate',
    'jsonpointer',
]

setup_requires = ['pytest-runner']

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
    author_email="eng-github@riverbed.com",
    packages=[
        'reschema',
    ],
    package_dir={'reschema': 'reschema'},
    scripts=[
        'bin/reschema-doc',
        'bin/relint'
    ],
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'test': test,
        'doc': doc,
        'dev': test + doc,
        'all': [],
    },
    setup_requires=setup_requires,
    tests_require=test,
    cmdclass={"pytest": PyTest},
    url="http://pythonhosted.org/steelscript",
    keywords='reschema',
    license='MIT',
    platforms='Linux, Mac OS, Windows',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Documentation',
    ],
    python_requires='>3.5.0',
)
