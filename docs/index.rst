.. reschema documentation master file, created by
   sphinx-quickstart on Fri Apr 11 08:09:14 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to reschema's documentation!
====================================

``reschema`` is a library for parsing reschema service definition
objects that describe a REST API.  The service defintion format is
described in fully in :doc:`specification`.  The package includes
tools for load and processing service definitions, generating API
documentation, and validating data according to schemas defined in the
service defintion.

Quick example:

.. code-block:: python

   # Load a service definition for a 'Bookstore' service
   >>> bookstore_def = ServiceDef.create_from_file('bookstore.yaml')

   # Get the 'author' resource
   >>> author_res = bookstore_def.resources['author']

   # Define an author and validate that the format is correct
   >>> author = dict(id=5, name='John Doe')
   >>> author_res.validate(author)

This Python module is useful for processing service definition files,
but it is frequently used in conjunction with ``sleepwalker``, another
module that provides a simple interface for interacting with servers
that implement services according to a reschema-based service definition.

Tools
-----

.. toctree::
   :maxdepth: 1

   specification
   module
   reschema-doc
   relint
   jsonschema

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

License
-------

This reschema documentation is provided "AS IS"
and without any warranty or indemnification.  Any sample code or
scripts included in the documentation are licensed under the terms and
conditions of the MIT License.  See the :doc:`license` page for more
information.
