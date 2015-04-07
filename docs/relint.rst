relint
======

relint is a rest-schema linter.

Usage
-----

.. code::

    $ relint -h
    usage: relint [-h] [--verbose] [-r RELATED] filename

    positional arguments:
      filename              RestSchema file to process

    optional arguments:
      -h, --help            show this help message and exit
      --verbose, -v         print status messages, or debug with -vv
      -r RELATED, --related RELATED
                            JSON doc source file

Note '-r RELATED' may be specifed multiple times to load multiple dependencies

Example:

.. code::

    $ relint -r s1.yaml -r s2.yaml main.yaml

This will check 'main.yaml', which has references to 's1.yaml' and 's2.yaml'

Rules
-----
.. toctree::
   :maxdepth: 1

   relint_rules
