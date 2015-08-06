Service Definition Specification
================================

Overview
--------

This document describes a schema for defining a REST API.  This schema,
also known as a service definition, is designed with the following goals
in mind:

* Web-browsable and searchable documentation across all products and
  versions
* Product / service specific REST APIs
* Uniform structure for all resource calls
* Support for automated document generation
* Allow definition of hyperlinks between services
* Enable validation and simplified REST usage via language specific
  libraries

Background
----------

REST APIs provide a popular and convenient menas of access to configuration
and monitoring of servers and services, but they are only as good as they
are usable by clients.  First and foremost, good documentation is required
and gives an important first impression that the APIs are well engineered
and supported.  Beyond good documentation, good supporting client libraries
further enhance the programmer's experience in interacting with an API.

Documentation
^^^^^^^^^^^^^

REST API documentation, like documenting SOAP or SNMP, is often a painful
and laborious process.  A fully featured API for a product may involve hundreds
of calls that need to be properly documented, with more calls added with
each release.  For each call, the list of acceptable parameters must be
documented, as well as the format of request and response objects.

In addition, documenting the individual calls is often insufficient, as
accomplishing a task may requiring the caller to issue a series of calls.
For example, running a report on Profiler involves connecting to the device,
creating a report object with the appropriate criteria, polling for status
until the report is done, then retrieving the results.  Documenting such
tasks will often be the first place users will look to get an understanding
of how to interact with a device via REST APIs.

In products using v2.0 or later of our API definition schema, the documentation
strings are embedded directly in the schema, or referenced from the schema
in external files.  The schema also includes type information and value
constraints, all of which can be leveraged to produce documentation or
validate data.  Due to the standardized location of documentation within
the schema, documentation is generated automatically rather than
manually transferred into an external format.

Supporting Client Libraries
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Working directly with REST APIs is a great improvement over technologies
like SNMP and SOAP.  It is possible to make REST calls directly with command
line tools such as ``curl`` and ``wget``, or in many cases simply with a web
browser.

However, writing extensive programs by manually coding support for REST
can quickly get out of hand.  In particular, hand-crafting the URLs of
REST resources is similar to embedding magic numbers in code.  It's doable
on a small scale, but it is error prone and difficult to maintain as the
application changes in size and the resource definitions change.

Many services that offer a REST API also provide client-side libraries that
mirror the REST API.  These libraries are often provided in multiple languages,
allowing client developers choice.  Use of the libraries enables developers
to work with interfaces and objects that are more native to the language
they are developing in, abstracting away the REST-ness of the API being
programmed against.

However, development and maintenance of the client libraries themselves can
become a burden on the server-side developers.  An out-of-date or incomplete
library is of no use to client developers.

As such, it is critical to enable the development of client-side
libraries that need minimal or perhaps *no* changes at all as APIs
change or new APIs become available.  This is made possible by the schema
supporting Hypertext As the Engine of Application State (HATEOAS) through
link and relationship definitions.

Specification
-------------

This specification defines a JSON object that fully describes the REST
resources associated with a single version of a service.  This JSON
object is referred to as the ``service definition``.

The ``service definition`` is used to generate REST API documentation as well as
enable the development of client-side libraries that can parse the
schema and eliminate the hand-coding of resource URLs and links.

This schema will cover the following topics:

* Full resource specification
* Specification for a distinct API version
* Tasks that involve a series REST calls
* Examples, etc.

Documentation Conventions
^^^^^^^^^^^^^^^^^^^^^^^^^

This document uses `RFC 2119 <https://tools.ietf.org/html/rfc2119>`_-style
terminology, with the following specifics:

    **MUST**:
        Indicates that implementations MUST return an error if the condition
        is not met.
    **SHOULD**:
        Means that implementations MUST allow deviations from the condition,
        but MAY issue a warning.  Tools supporting best practices such as
        a linter MUST report non-conformance as a warning if non-conformance
        can be detected (some conditions relay on outside knowledge of
        the system such as whether combinations of fields create unique keys,
        and therefore cannot be detected programmatically).

In practice, MUST means that ``reschema`` requires it, and SHOULD
means that ``reschema`` does not require it but ``relint`` (the linter
for reschema) will complain about it if it possibly can.

JSON Schema
^^^^^^^^^^^

The ``service definition`` heavily relies on :doc:`jsonschema`
for describing data types.  Similar to C ``struct``, at
a minimum a ``json-schema`` lays out all the elements and types of a
JSON object.

This representation is used to describe both simple strings and numbers as well
as complex data types in JSON.  The schema may also include documentation for
each attribute, as well as constraints on data values.

For example, the following simple ``json-schema`` defines a JSON object
representing an ``address``:

.. code-block:: json

    {
        "type": "object",
        "id": "address",
        "properties" : {
            "street" : { "type": "string", "description": "Street Address" },
            "city" : { "type": "string", "description": "City" },
            "state" : { "type": "string", "description": "State", "pattern": "[A-Z][A-Z]" },
            "zip" : { "type": "string", "description": "Zip Code (5-digit)", "pattern": "[0-9][0-9][0-9][0-9][0-9]" }
        }
    }

A JSON object conforming to this schema:

.. code-block:: json

    {
        "street" : "123 High Street",
        "city" : "Springfield",
        "state": "IL",
        "zip": "12345"
    }

The examples in this document are presented in YAML format rather than JSON,
as YAML is easier to read and is close enough to JSON that there is no ambiguity
in meaning.  The YAML equivalent of the above examples is shown below:

Address schema in YAML:

.. code-block:: yaml

    type: object
    properties:
       street: { type: string, description: "Street Address" }
       city: { type: string, description: "City" }
       state: { type: string, description: "State", pattern: "[A-Z][A-Z]" }
       zip: { type: string, description: "Zip Code (5-digit)", pattern: "[0-9][0-9][0-9][0-9][0-9]" }

Address object in YAML:

.. code-block:: yaml

    street: "123 High Street"
    city: "Springfield"
    state: "IL"
    zip: "12345"


See :doc:`jsonschema` for a brief introduction and pointers to the IETF drafts.

REST API Service Definition Object (``service definition``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section describes the ``service definition`` object in detail.

Service Definition Object
"""""""""""""""""""""""""

The ``service definition`` object has the following structure:

.. code-block:: yaml

    $schema: <string>,
    id: <string>,
    provider: <provider>
    name: <string>,
    version: <string>,
    title: <string>,
    description: <string>,
    defaultAuthorization: <string>,
    documentationLink: <string>,
    types: { ... },
    resources: { ... },
    errors: [ ... ],
    tasks: [ ... ],


The properties are defined as follows:

.. list-table::
   :header-rows: 1

   - * property
     * type
     * description
     * notes
   - * $schema
     * string
     * URI of the JSON Schema describing the format of this document
     * This document describes http://support.riverbed.com/api/service_def/2.3
   - * id
     * string
     * URI where the official copy of this document can be found
     * Serves as the unique identifier for the service definition
   - * provider
     * string
     * Identifier of the organization that authored this document
     * Riverbed service definitions use 'riverbed', other organizations must
       use a globally unique identifier
   - * name
     * string
     * Name of the service provided by this REST API
     * Unique name within the namespace of the provider
   - * version
     * string
     * Version string of the REST API described
     *
   - * title
     * string
     * One line description
     *
   - * description
     * string
     * More verbose description of the API
     *
   - * defaultAuthorization
     * string
     * Default authorization for all resources and links if not specified.
     * Valid values: required, optional, none
   - * documentationLink
     * string
     * URL for online documentation for this API
     *
   - * types
     * object
     * common data types used by resource requests and/or responses
     *
   - * resources
     * object
     * resources schemas defined for the various REST resources supported
     *
   - * errors
     * array
     * documentation of possible error codes when resource requests fail
     *
   - * tasks
     * array
     * documentation of more complex tasks involving multiple resource calls
     *

The heart of the ``service definition`` object is in the ``resources`` section.

Service definition 'id'
"""""""""""""""""""""""

The 'id' property serves two purposes:

   #. URI where the official copy of the service definition document can be found
   #. Globally unique identifier for the service definition

As a unique identifier, the 'id' is used when defining links and relations
to other services via the '$ref' or 'resource' properties.

The Riverbed format for the 'id' is show below:

    http://support.riverbed.com/apis/<name>/<version>

Service Path
""""""""""""

The ``service path`` is the fully qualified path (URI) that is the base for all
REST resources of the same hosted service.

As a simple example, the following is the service path for a 'bookstore'
service hosted by a server 10.1.2.3::

    https://10.1.2.3/api/bookstore/1.0

The service *path* is implementation specific and thus fully separate
from the service *definition*.  For this reason, the fully qualified
service *path* is not specified as part of the definition and is instead
replaced with the '$' character when defining the templates for building
URIs for the various resources that make up the service.

As will be described in more detail in later sections, each resource
definition includes a 'self' link that defines the URI template for
this resource.  A 'books' resource in the 'bookstore' service might have the
following self link:

.. code-block:: yaml

    resources:
       books:
          links:
             self: { path: '$/books' }

The '$' in the path must be replaced at runtime based with the fully qualified
service path.

Note that within a single network, a single service *definition* may
be implemented multiple times as different services, each with a unique service
*path*.  The *path* itself has a {server} component and a {relpath}::

    {server}{relpath}

    https://10.1.2.3/api/bookstore/1.0

    server := 'https://10.1.2.3'
    relpath := '/api/bookstore/1.0'

For example:

**multiple instances on the same server**
    The {relpath} component must be different for each instantiation of the service.
**one instance per server, but multiple servers**
    Since the service definition is implemented on different servers, the {server} component of the service path will be unique.  The {relpath} component therefore may (but need not) be the same across all servers.
**multiple instances on multiple servers**
    A generalization of the above two cases.

The breakdown of the {relpath} component is {server}
(ie. implementation) specific, meaning that two different servers may
actually assign different paths for implementing the same service
*definition*.

Note that the full generalization of this means that some servers may
implement a single instance and others may implement multiple
instances.  In this generalization, a client that is attempting to
access multiple services in the network, the client must be able to
determine the service path for any service that it might connect to.

See the section on service path resolution below for further details.

Types
"""""

The ``types`` property is used to define common data types that are
used by request or response objects.  The ``types`` value is a
JSON object where each property name defines a unique type.

.. code-block:: yaml

    types:
       <type-name> : <json-schema>
       <type-name> : <json-schema>

For example, the following defines two types, "address" and "phone":

.. code-block:: yaml

    types:
       address:
          type: object

          properties:
             street:
                type: string
                description: "Street Address"
             city:
                type: string
                description: "City"
             state:
                type: string
                description: "State"
                pattern: "[A-Z][A-Z]"
             zip:
                type: string
                description: "Zip Code (5-digit)"
                pattern: "[0-9][0-9][0-9][0-9][0-9]"

       phone:
          type: string
          pattern: "[0-9]{3}-[0-9]{3}-[0-9]{4}"

A ``type`` defines only the structure of a data object, it does not have any
associated behaviors.  Defining types allows the same fundamental data types
to be referenced by other types and resources, in this service definition
as well as in others.

Resources
"""""""""

The ``resources`` section defines a schema for each REST resource
exposed by the service.  Note that a *resource schema* defined in the
schema may map to multiple *concrete resources* supported by the
server.  This relationship is analogous to *classes* and *objects*.
For example, the ``book`` resource schema defines the properties
associated with a book resource, including the data type as well as
the behaviors associated with a book.  The server will have multiple
actual instances, or books, all described by this resource schema.

Whereas a *type* defines only the structure of a data object, a
*resource* binds a data object to a resource as supported by a server
via the ``self`` link and allows the definition of related actions that
can be performed via additional links, as well as relations to other resources.

A ``resource`` definition is an extension of a ``json-schema``, adding ``links``
and ``relations``.  The following properties are used to describe a ``resource``:

.. list-table::
   :header-rows: 1

   - * property
     * description
   - * type
     * json-schema type: object, string, array, number
   - * description
     * text description of this resource
   - * links
     * one or more named links applicable to this resource
   - * links.self
     * required link providing the URI template for an instance of this resource
   - * relations
     * one or more named relations to other resources applicable to this resource

When in the context of a resource, additional nested schemas are
defined when the ``type`` is ``object`` or an ``array``.  These *nested*
schemas do not have a self link, however they may have other
links and relations defined.  This is described in more detail in later sections.

A simple resource schema for ``book`` is shown below:

.. code-block:: yaml

    resources:
       book:
          description: "Defines a book resource"

          type: object
          additionalProperties: False
          required: [ id, title ]
          properties:
             id:
                type: number
                readOnly: True
             title: { type: string }
             publisher_id: { type: number }
             author_ids:
                # Array of author ids, associated with this book
                type: array
                items: { type: number }

             chapters:
                type: array
                items:
                   type: object
                   additionalProperties: False
                   properties:
                      num: { type: number }
                      heading: { type: string }

          links:
             self:
                # Base URI for an instance of a book
                path: "$/books/items/{id}"

             get:
                # Get the current data representation of a book
                # path defaults to "self" at /books/items{id}
                method: GET
                response: { $ref: '#/resources/book' }

             set:
                # Replace the data representation for a book
                # path defaults to "self" at /books/items/{id}
                method: PUT
                request: { $ref: '#/resources/book' }
                response: { $ref: '#/resources/book' }

             delete:
                # Link to delete a book instance
                # path defaults to "self"
                method: DELETE

             purchase:
                path: "$/books/items/{id}/purchase"
                method: POST
                request:
                   type: object
                   properties:
                      num_copies: { type: number }
                      shipping_address: { $ref: '#/types/address' }

                response:
                   type: object
                   properties:
                      delivery_date: { type: string }
                      final_cost: { type: number }

          relations:
             publisher:
                resource: '#/resources/publisher'
                vars: { id: '0/publisher_id' }


Links
'''''

A link defines the set of actions and other resources that are related
to an instance of a resource schema (a concrete resource).  For
example, the ``book`` resource defines the ``get`` link which describes how
a client retrieves a copy of the data representation for a particular
book instance.

A link may have the follow properties:

.. list-table::
   :header-rows: 1

   - * property
     * description
   - * path
     * URI template for the address of an instance of this resource
   - * description
     * Description of the purpose of this link
   - * method
     * Applicable HTTP method used to exercise this link
   - * request
     * json-schema for parameters associated with a GET, or the body of a POST
   - * response
     * json-schema for the response from a server for this link

There are several possible combinations of the above properties that
have slightly different meanings.

If the "path" is omitted, the "path" associated with the "self" link is
used.

The link ``path`` may include one or more variables in the base URL:

* /books/items/{id} - one variable {id}
* /books/items/{bookid}/chapter/{num} - two variable {bookid} and {num}

All variables must be resolved to values in order to exercise the
link.  Variables are first resolved from the data associated with a
resource.

For example, the ``book`` resource is defined as follows (abbreviated):

.. code-block:: yaml

    resources:
       book:
          description: "Defines a book resource"

          type: object
          additionalProperties: False
          required: [ id, title ]
          properties:
             id: { type: number }
             title: { type: string }
             publisher_id: { type: number }
             author_ids: ...
             chapters: ...

          links:
             self:
                description: "Base URI for an instance of a book"
                path: "$/books/items/{id}"

             get:
                description: "Get the current data representation of a book"
                method: GET
                response: { $ref: '#/resources/book' }

             set:
                description: "Update a book from a data representation"
                method: PUT
                request: { $ref: '#/resources/book' }
                response: { $ref: '#/resources/book' }

             purchase:
                path: "$/books/items/{id}/purchase"
                method: POST
                request:
                   type: object
                   properties:
                      num_copies: { type: number }
                      shipping_address: { $ref: '#/types/address' }

                response:
                   type: object
                   properties:
                      delivery_date: { type: string }
                      final_cost: { type: number }

The ``links`` section above defines four links:

   ``self``
        defines the path for accessing a book resource.  Note that the path defines a single variable {id} which refers to the property in the book resource definition ``resources.book.properties.id``.
   ``get``
        retrieve the data representation for a book using the GET method.
   ``set``
        update a book from a data representation using the PUT method.  An updated data representation is returned.
   ``purchase``
        initiate a book purchase using the POST method at the URL "$/books/items/{id}/purchase".  Since this link is defined on a ``book`` resource, the {id} in the URL is filled based upon a specific book data representation.

The ``$ref`` syntax
:::::::::::::::::::

Links frequently use ``$ref`` to refer to resources and types defined
elsewhere in this or other service definitions.  The syntax of a fully
qualified reference is simply the ``id`` of the service definition (a
URL) followed by a fragment that is a JSON pointer to some JSON
schema within the service definition at that ``id``.

There are three supported formats of the reference, which mirrors standard
URL page resolution:

.. list-table::

   - * **Local**
     * ``#{jsonpointer}``
     * Same service definition
   - * **Provider**
     * ``/{name}/{version}#{jsonpointer}``
     * Same provider, different service
   - * **Full**
     * ``{id}#{jsonpointer}``
     * Fully qualified reference

The ``self`` link
:::::::::::::::::

.. list-table::
   :header-rows: 1

   - * path
     * params
     * method
     * request
     * response
   - * required
     * optional
     * n/a
     * n/a
     * n/a

The ``self`` link documents the address of a resource described by this
resource schema.  It must be defined for every resource schema and includes
the ``path`` property which defines a URI template.

If the URI template includes variables, the variables should match properties
in the resource's data representation.  For example, in the book self link
below, the ``{id}`` variable matches the book's ``id`` property.

.. code-block:: yaml

    resources:
       info:
          links:
             # No variables in this resource
             self: { path: "$/info" }

       book:
          type: object:
          properties:
             id: { type: number }
             ...
          links:
             # {id} matches the resource property defined at book.properties.id
             self: { path: "$/books/items/{id}" }

       book_chapter:
          type: object:
          properties:
             bookid: { type: number }
             num: { type: number }
             ...
          links:
             # {bookid} matches the resource property book_chapter.properties.bookid
             # {num} matches the resource property book_chapter.properties.num
             self: { path: "$/books/items/{bookid}/chapter/{num}" }

Self links are only allowed at the root of a resource schema.

The ``params`` property of the link defines additional qualifiers when
addressing a resource.  These qualifiers are typically filter parameters
that select a subset of a collection, or restricited set of fields.

For example, the ``books`` resource is shown below (``books`` is the plural
collection not to be confused with the singular ``book`` resource):

.. code-block:: yaml

    resources:
       books:
          type: array
          items:
             type: object
             properties:
                id: { type: number, readOnly: true }
                title: { type: string }

          links:
             self:
                path: "$/books"
                params:
                   # Allow filtering by author id or title
                   author: { type: number }
                   title: { type: string }

Parameters are expressed as URI parameters.

Retrieve only books written by author id 1::

    GET /books?author=1

Retrieve only books written by author id 1 and have "Bunnies" in the title::

    GET /books?author=1&title=Bunnies

Note that the interpretation of the parameters is dependent
on the server implementation.  The meaning of the ``title`` parameter
could be an exact match or a substring match.  The schema should
document such details that are relevant to client developers.

Note also that ``/books`` is the collection, not ``/books/items``, so
the parameters apply to ``/books``.  The ``/books/items`` path only
appears when a specific element of the collection's URI is constructed.

Standard links: get, set, create, delete
::::::::::::::::::::::::::::::::::::::::

.. list-table::
   :header-rows: 1

   - * path
     * method
     * request
     * response
   - * n/a
     * required
     * optional
     * optional

The standard resource operations of ``get``, ``set``, ``create``, and
``delete`` are all defined as links with an HTTP ``method`` and ``path``
equal to the path of the ``self`` link.  The ``path`` property is not
provided as these operations are always relative to the resource in
question, thus are available at the self link path.

.. code-block:: yaml

    resources:
       info:
          links:
             get:
                method: GET
                response: { $ref: '#/resources/info' }
             set:
                method: PUT
                request: { $ref: '#/resources/info' }
                response: { $ref: '#/resources/info' }

The ``request`` schema is used to pass data to the server.  For a ``GET``, the
``request`` must be a flat object whose properties define the valid URL parameters.
For a ``POST``, the ``request`` may be any valid ``json-schema`` and is provided
in the body of the message.

The ``response`` schema defines the expected response on success.  Errors
are handled separately (see the section on Errors).

Verbs
:::::

.. list-table::
   :header-rows: 1

   - * path
     * method
     * request
     * response
   - * required
     * required
     * optional
     * optional

This type of link is commonly used for verbs like "reboot", where it
is difficult to map normal REST resource (noun) semantics to the URI.
The action is performed using the defined "method" at the "path"
provided.  The "path" must define a unique resource (by URI template)
and must be prefixed by the "path" of the "self" link.

The method will normally be a POST:

.. code-block:: yaml

    resources:
       book:
          links:
             purchase:
                path: "$/books/items/{id}/purchase"
                method: POST
                request:
                   type: object
                   properties:
                      num_copies: { type: number }
                      shipping_address: { $ref: '#/types/address' }

                response:
                   type: object
                   properties:
                      delivery_date: { type: string }
                      final_cost: { type: number }

``$merge`` syntax
:::::::::::::::::

Services may leverage ``$merge`` as a means for combining two schemas.  This should
be regarded as a preprocessing step that results in a valid JSON schema.

The syntax is as follows:

.. code-block:: yaml

   $merge:
      source: <object>
      with: <object>

The source and with are objects that are combined to form a new object
in it's place.  The with object is merged into the source object according to the
following rules:

For each property in with:
   #. If either source or with is a $ref, dereference the target first
   #. If a property is in source and the value of with is None, the
      property is removed from the final object.
   #. If a property is in source, and both values are in turn objects,
      recurse into the objects and merge recursively
   #. Otherwise, set store the value of with in the final object

As an example:

.. code-block:: yaml

   $merge:
      source:
         x: 1
         y: 2
         sub:
            a: 10
            b: 20
      with:
         x: 0
         z: 3
         sub:
            a: 5

Results in:

.. code-block:: yaml

   x: 0
   y: 2
   z: 3
   sub:
      a: 5
      b: 20

Relations
'''''''''

A relation defines another resource that is related to the given resource,
usually based on the data representation of the given resource.  A relation
is essentially a pointer to another resource that may be followed to get
to the other resource.

The primary use of defining relations is to explicitly define
relations based on a given resource data representation, rather than
implying relationships via documentation.  For example, in the ``book``
resource, the ``publisher`` relation explicitly
describes that the ``publisher_id`` property of a book resource can be
used to reach the associated publisher resource:

.. code-block:: yaml

    resources:
       book:
          description: "Defines a book resource"

          type: object
          additionalProperties: False
          required: [ id, title ]
          properties:
             id: { type: number }
             title: { type: string }
             publisher_id: { type: number }
             ...

          relations:
             publisher:
                resource: '#/resources/publisher'
                vars: { id: '0/publisher_id' }

       publisher:
          type: object
          properties:
             id: { type: number }
             name: { type: string }

          links:
             self: { path: "$/publishers/{id}" }

As another example, the ``author`` resource defines the ``books`` relation
that fills in the ``author`` parameter that is supported by the ``books`` self
link:

.. code-block:: yaml

    resources:
       author:
          type: object
          properties:
             id: { type: number }
             name: { type: string }

          relations:
             # the entire list of authors
             instances:
                resource: '#/resources/authors'

             # the collection of books written by this author
             books:
                resource: '#/resources/books'
                vars: { author: "0/id" }

Each relation must define the ``resource`` property.  This identifies the related
resource by name.  The ``instances`` relation links to the ``authors`` resource
(note again the singular ``author`` vs the plural ``authors``, two different
resources).

The phrase "following a resource relation" is used to describe the process:

   #. Retrieve the data representation for a known "source" resource (say '/author/3')
   #. Examine the schema for the "target" resource and parse the desired relation definition (say the 'books' relation)
   #. Examine the ``self`` link of the target resource and fill in the necessary parameters based on the data representation of the source resource using the relation ``vars`` mapping.
   #. Retrieve the data representation for the target resource using the fully resolved ``self`` link.

Syntax
::::::

A ``relation`` is defined as follows:

.. code-block:: yaml

    resources:
       <resource>:
          relations:
             <relation_name>:
                resource: <target_resource>
                vars:
                   <target_var>: <rel_json_pointer>
                   <target_var>: <rel_json_pointer>
                   ...

.. list-table::

   - * **relation_name**
     * Unique name within this set of relations
   - * **target_resource**
     * Reference to the target resource, see below
   - * **target_var**
     * Variable in the target resource's self link
   - * **rel_json_pointer**
     * Relative JSON pointer to use to fill in the target_var based on a data representation of the source resource

``resource`` references
:::::::::::::::::::::::

For relations, the ``resource`` property is similar to link references via
``$ref``.  The primary difference is that the target of a ``resource`` property
must point to another resource, it cannot be a type.

When following a resource relation, there are two types of resolution that
must occur:

**schema resolution**
    identifying the *general* service definition schema that describes the target resource
**URI resolution**
    identifying the full URI of the *particular* target resource in the context of a data representation of the source resource

For example, returning to the author/relations/books example, the schema
and path are resolved as follows:

.. list-table::

   - * **source schema**
     * http://support.riverbed.com/apis/bookstore/1.0#/resources/author
   - * **source URI**
     * https://10.1.2.3/api/bookstore/1.0/author/12
   - * **source data rep**
     * ``{ id: 12, name: "John Smith" }``
   - * **target schema**
     * http://support.riverbed.com/apis/bookstore/1.0#/resources/books
   - * **target URI**
     * https://10.1.2.3/api/bookstore/1.0/books?author=12

The *target URI* above is based on the data representation of the source
data representation and was built from the self link of the 'books' resource.

``$`` and URI resolution across services
::::::::::::::::::::::::::::::::::::::::

In the simplest case, the '$' in the self link of a target resource is
replaced with the service URI of the source resource.  However, it is
possible to support links and relations from one service to another where
some services are potentially on different servers.

TBD

``full`` and ``instances`` relations
::::::::::::::::::::::::::::::::::::

The ``full`` relation is a special relation that refers to the full
resource associated with a partial representation of that resource.  This is
used most frequently with collections.

Likewise the ``instances`` relation is a special relation that refers
to the full collection of resources of which the given resource is just
one.

For example, consider the ``books`` and ``book`` resources:

.. code-block:: yaml
   :emphasize-lines: 11,20

    resources:
       books:
          type: array
          items:
             type: object
             properties:
                id: { type: number, readOnly: true }
                title: { type: string }

             relations:
                full:                       # "full" relation on collection
                   resource: '#/resources/book'
                   vars: { id: "0/id" }
          ...

       book:
          type: object
          ...
          relations:
             instances:                     # "instances" relation on element
                resource: '#/resources/books'

Notice that the ``full`` relation is a nested relation defined on the
array *item* and leverages the item ``id`` property to link to the full
book resource.

The ``full`` relation may be used in other contexts as well.  For
example, the link from a book to it's publisher via the publisher_id
could be represented as follows:

.. code-block:: yaml
   :emphasize-lines: 9

    resources:
       book:
          type: object
          properties:
             id: { type: number }
             publisher_id:
                type: number
                relations:
                   full:                    # "full" relation on a property
                      resource: '#/resources/publisher'
                      vars: { id: "0" }

Mapping values to self link parameters
::::::::::::::::::::::::::::::::::::::

The ``vars`` property may be specified to map values from a data
representation of the soruce resource to variables or parameters in the
target resource's self link.  This mapping is what makes it possible to
automatically jump from one resource to a related resource.

Let's look in detail at the ``author.relations.books`` relation.  The
relation's target resource is ``books``.  The ``books`` self.link is shown
below and was used as an example above in the "Self link" section:

.. code-block:: yaml

    resources:
       books:
          links:
             self:
                path: "$/books"
                params:
                   # Allow filtering by author id or title
                   author: { type: number }
                   title: { type: string }

Looking at the list of supported parameters, the ``books`` resource
supports filtering based on the author id via the ``author`` parameter.
So, to get the list of books associated with an ``author`` resource, the
``id`` properties of the author data representation should be used for the
``books.links.self.params.author`` parameter.  This is represented in the
``author.relations.books.vars`` property:

.. code-block:: yaml

         books:
            resource: '#/resources/books'
            vars: { author: "0/id" }

The above indicates that ``author`` in the ``books`` resource should be
filled in with the ``author`` data representations ``id`` property.
The "0/id" is a relative JSON pointer, the "0" indicates to start
at the same level as the relation definition, and then traverse using
the "id".  See the appendix on relative JSON pointers for more details
on the syntax.

Example relation: publisher of a book
:::::::::::::::::::::::::::::::::::::

The following example shows how to define a relation from a book
to the publisher resource for that book:

.. code-block:: yaml

    resources:
       book:
          description: A book object
          type: object
          properties:
             id: { type: number }
             title: { type: string }
             publisher_id: { type: number }
             ...

          relations:
             publisher:
                resource: '#/resources/publisher'
                vars:
                   id: '0/publisher_id'

    publisher:
       ...
       links:
          self: { path: "$/publishers/{id}" }

To start, the above defines a relation from a singular ``book`` resource
to the singular ``publisher`` associated with that book based on the
``publisher_id`` property of a ``book``.

``relations.publisher.resource`` indicates that the related resource is
called ``publisher``, and the ``vars`` indicates that the ={id} variable
in the self link path of the target resource should be filled in using
the ``publisher_id`` of a data representation for a book.

Singletons versus instances
'''''''''''''''''''''''''''

A resource schema may define either a single resource instance or
multiple instances depending on the ``self`` relation.  If the ``self``
path template does not contain any variables, than the resource is a
singleton.  If ``self`` includes one or more variables, than the
resource is multi-instance, with each instance addressable by filling
in all of the variable in the template.

For example:

* "/info" describes a singleton
* "/books" describes a singleton, even though the response data
  representation is a collection (of books), the resource itself is
  a singleton
* "/books/items/{id}" describes a multi-instance resource indexed by
  the variable {id}
* "/books/items/{id}/chapter/{num}" describes a multi-instance
  resource indexed by the tuple {id} and {num}.

Note that "/books/items/1" is a separate resource from
"/books/items/1/chapter/2", despite the fact that the former is a
prefix of the latter.  Each of these two resources is described by
different resources (``book`` and ``book_chapter``, see the appendix).

Collections and nested links and relations
''''''''''''''''''''''''''''''''''''''''''

A collection is a common resource pattern that defines two resources,
one for accessing an individual element in the collection, the second
for accessing the collection as an array.  The above "/books/items/{id}" is
an example of a collection element and "/books" is the matching collection.

In the simplest case, ``links`` and ``relations`` are defined at the same
level as the base "type" property of the resource:

.. code-block:: yaml
   :emphasize-lines: 2,3,8,18

    resources:
       info:                        # non-collection, non-element resource
          type: object              # of type object
          properties:
             owner: { type: string }
             email: { type: string }

          links:                    # Links at top level
             self: { path: "$/info" }
             get:
                method: GET
                response: { $ref: '#/resources/info' }
             set:
                method: PUT
                request: { $ref: '#/resources/info' }
                response: { $ref: '#/resources/info' }

          relations:                # Relations at top level
             books: { resource: '#/resources/books' }
             authors: { resource: '#/resources/authors' }

Such top-level links apply to an instance of the resource.  However,
links and relations may also be defined at other locations within the
data.  They are defined at the same level as any ``type`` keyword which begins
the definition of the structure of some subset of the data.

These nested links and relations are necessary to define links and
relations based on a specific item in an array.

Consider the structure of the ``books`` resource:

.. code-block:: yaml

    resources:
       books:
          type: array
          items:
             type: object
             properties:
                id: { type: number, readOnly: true }
                title: { type: string }

::

    GET /books
    [ { id: 1, title: 'My favorite book' },
      { id: 2, title: 'My other favorite book' } ]

The data representation for ``books`` returns an array of data, where each
array element includes the book id and the book title.  If the client wants
to examine the authors associated with each book, the full ``book`` resource
must be retrieved for each item in the array, using the ``id`` property of
the array item as the value for {id} in the book self link.  Since
the data represents multiple books (2 in the above example), and the
``book`` resource can only represent one book, the relation must be described
in a way relative to each array element separately.

This relation can be expressed in the ``service definition`` in one of two
ways:

.. code-block:: yaml
   :emphasize-lines: 5,10,15

    resources:
       books:
          type: array
          items:
             type: object               # type of each individual array item
             properties:
                id: { type: number, readOnly: true }
                title: { type: string }

             relations:                 # relation on each array item
                book:
                   # Build a book link from the 'id' property
                   resource: '#/resources/book'
                   vars:
                      id: "0/id"        # this array item's 'id' property

In this variation, the relation is defined at the same level as the
``type: object``, thus the value of the target ``id`` is taken from the
array item ``id`` property.

An alternative is to push the relation definition one level deeper:

.. code-block:: yaml
   :emphasize-lines: 10,15

    resources:
       books:
          type: array
          items:
             type: object
             properties:
                id:
                   type: number
                   readOnly: true
                   relations:           # Relation on an object property
                      book:
                         # Build a book link from the 'id' property
                         resource: '#/resources/book'
                         vars:
                            id: "0"     # this number value
                title: { type: string }

Other than moving the relation definition deeper into the data
representation structure to the same level as the ``type: number`` for
the id property, the ``vars.id`` value must change to reflect the fact
that the entire data value *at this point* in the data structure is used.

In general, it is preferable to put the relation definition as close to
the root as possible (the first variation), simply for readability,
but links and relations can be defined

There are 2 possible "book" relation links, one for each entry in the response.
To resolve the "book" path, first select an entry in the array, then resolve
the path.  For example, selecting "101" in the array, the "book" path will
be "/books/items/101".  The "{$}" indicates that array value should be used.
This is described in more detail in the next section.

Paths
'''''

The "path" property associated with a link definition defines the URI
template for the link.  The template may be a static path such as
"$/info", or it may be a path with variables such as "$/books/items/{id}" or
"$/books/items/{bookid}/chapter/{num}".

A simple static path with no variables:

.. code-block:: yaml

    resources:
       info:
          links:
             self: "$/info"

In order to evaluate a link, all variables in the link must be
resolved to values.  The values are taken first either from a data
representation of the associated resource, or provided by the client
when resolving the link.

When resolving variables from a data representation, the relative location of
the link definition within the resource schema definition is taken
into account.  This is discussed further below.

.. warning::
    The following text has never been implemented, and is probably not needed
    now that we have JSON relative pointers.  Contact the RTC before using.

    DEPRECATED?: "{$}" indicates that the value of the instance data
    (relative to the link definition).  See the examples below.

The "path" property may take two forms, direct or indirect.  In the
direct form, the "path" property is a string defining a URI template
conforming to `RFC 6750 <http://tools.ietf.org/html/rfc6570>`_.
Simply put, this is a URI with zero or more variables in curly braces
that must be replaced.  Only variables at the same level as the link definition
can be resolved in the direct form.

Shown below is a path with a single variable taken from instance data.
The "{id}" variable is resolve by inspecting the data representation
associated with a given instance of a "book" resource:

.. code-block:: yaml
   :emphasize-lines: 5,9

    resources:
       book:
          type: object
          properties:
             id: { type: number }               # Type information for 'id'

          links:
             self:
                path: "$/books/items/{id}"      # Use of 'id' in the path

In the *indirect* form, the path is an object with two properties as follows:

.. code-block:: yaml

    path:
       template: <string>
       vars:
          <var>: <relative JSON Pointer>
          <var>: <relative JSON Pointer>
          ...

In this second form, the URI template is defined in the "template"
property.  However, the variables are resolved first by looking the in
"vars" object, then a resource data representation, then finally to
other sources such as the user.  (This form is necessary since the
allowed characters for variables in a URI template is severely
restricted and does not allow for the "/", thus this layer of
indirection is needed.)

The "vars" property defines variables using relative JSON pointers.
This allows referencing instance data at other locations within a complex
JSON data structure.

**TODO**: Example for the indirect form.

Errors
""""""

The mechanism for defining errors and the format of the responses closely follows
the Problem Details IETF draft (`draft-ietf-appsawg-http-problem`_).

Service Defined Errors
''''''''''''''''''''''

A service definition may specify a list of errors that the service may generate.
The ``errors`` property occurs at the same level as ``resourcess``.

Each error definition has the following properties:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   - * property
     * description
   - * type
     * An absolute URI that identifies the error type.  When
       dereferenced, it SHOULD provide human-readable documentation
       for the error type.  Note that the ``type`` URI is not
       explicitly defined in the service defintion, it is implied
       based on the full service ``id``.

       This MUST be used as the primarly identifier for the error
       type.  Clients SHOULD NOT automatically dereference this
       URL.
   - * title
     * A short, human readable summary of the problem type.
   - * description
     * A detailed description of the error type suitable for
       documenation.  This text should describe in detail
       what causes the error to occur and identifies steps
       the client can take to fix the problem.
   - * properites
     * A dictionary of additional properties that may be
       included in the error response.  The value associated
       with each name is a schema that defines the structure
       of the property value in the response body.

       There is one special ``detail-values`` property that SHOULD be
       used to JSON schema that describes the structure of the
       ``values`` property that may be included in the error response

An example of an error definition:

.. code-block:: yaml

   id: 'http://support.riverbed.com/apis/bookstore/1.0'

   ...

   errors:
      invalid_username:
         title: "The specified username is invalid"
         description: >
            An attempt was made to access a resctricted resource
            using a username that is not valid.  This may be
            because there is no such account or because the
            account is disabled.  Check with an adminstrator
            for this device.
         properties:
            detail-values:
               type: object
               properties:
                  username: { type: string }

The full ``type`` for the above error would be
``http://support.riverbed.com/apis/bookstore/1.0/service.html#/errors/invalid_username``.
Note that the ``type`` links to the HTML rendering of the service definition, with
an anchor taking the user directly to the error defined within the service.

Error Responses
'''''''''''''''

If an error occurs while processing a request from a client, a server
will respond with an appropriate HTTP Status Code and the respond body
will provide additional details.

The structure of the error is as follows:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   - * property
     * description
   - * id
     * URI of the JSON schema for this error response.
   - * type
     * Absolute URI that identifies the error type.  This is the
       same as the type in the error definition.
   - * title
     * A short human readable summary of the problem type.  This
       text MUST NOT change except for purposes of localization.
   - * detail
     * A human readable explanation specific to this occurrence of the
       problem.  The string SHOULD contain dynamic information
       providing context for this occurrence.

       This SHOULD focus on helping the end user correct the problem,
       rather than providing debugging information.

       Clients SHOULD NOT attempt to parse this string.  Instead,
       extensions (see additionalProperties) should be provided.
   - * detail-values
     * A dictionary of name/values pairs that identify the unique
       information for this specific occurrence of the problem.

       In general, these values could be plugged into a format
       string to generate the ``detail`` above.

       The schema for the values SHOULD be defined in the
       error definition under "properties"
   - * *additional properties*
     * Other custom properties that may be returned in the error
       response.  The schema for these additional properties SHOULD be
       defined in the error definition under "properties".

An example error response:

.. code-block:: yaml

   type: "http://support.riverbed.com/apis/bookstore/1.0/service.html#/errors/invalid_username"
   title: "The specified username is invalid"
   detail: "'jdoe' is not a valid username"
   detail-values:
      username: "jdoe"

Additional Properties
'''''''''''''''''''''

As described above, the error response may contain *additional
properties* that provide additional information beyond what is
specified here.  For example, a resource that is used to process web
forms may include an addition "form_fields" property that allows the
server to enumerate customer error messages for multiple form fields.

The error definition:

.. code-block:: yaml

   errors:
      invalid_form:
         title: "Form data is invalid."
         description: >
            A form was posted that does not satisfy one or more
            constraints.  This may be values out of range, or may
            be an invalid combination of field values.
         properties:
            detail-values:
               type: object
               properties:
                  fields:
                     type: array
                     items: { type: string }

            form-fields:
               type: object
               description: >
                  Dictionary of form fields that failed validation.
                  The value for each field is a mesesage describing
                  why that field failed validation.
               properties:
                   message: { type: string}

An example error response:

.. code-block:: yaml

   type: "http://support.riverbed.com/apis/bookstore/1.0/service.html#/errors/invalid_form"
   title: "Form data is invalid."
   detail: "The following fields failed validation: SSN, email"
   detail-values:
      fields: [ "SSN", "email" ]
   form-fields:
      SSN: "Social security number must be provied"
      email: "The email address provided is not valid"

Versioning
^^^^^^^^^^

A ``service definition`` object represents the complete REST API reference for a single
version of a single service.  The top level "version" property describes
the version.  Each time the REST API version number is changed, a new
documentation object must be generated.

Two versions of the ``service definition`` for the same service (describing two versions
of the REST API) may be compared programmatically to produce a change set, including:

* added or removed resources / methods
* changes to existing methods
* changes to descriptions and links


Schema Best Practices
^^^^^^^^^^^^^^^^^^^^^

Always return an ``object``
"""""""""""""""""""""""""""

Always return an ``object``.  If the desired data type is number,
string, or array, wrap this in an ``object``.  This enables the
inclusion of meta data.

In the case of an array, the property of the ``object`` that is the array
should be named "items", as in:

.. code-block:: yaml

    resources:
        things:
            type: object
                properties:
                    items: {$ref: '#/resources/thing'}

**TODO**:

* Arrays and paging XXX

**TODO** - examples

Include all link variables in the data representation
"""""""""""""""""""""""""""""""""""""""""""""""""""""

This is particularly important for the ``self`` link, but applies as a
general rule.  This allows data representations to be
"self-describing" -- meaning that a client can determine the address
for a resource given the data representation and the schema for that
representation.

* ``book.links.self : { path: "$/books/items/{id}" }``
      * ``{id}`` should be in the book data representation
* ``book_chapter.links.self: { path: "$/books/items/{bookid}/chapter/{num}" }``
      * both ``{bookid}`` and ``{num}`` should be in the book_chapter data representation

Use plural for URI of collections
"""""""""""""""""""""""""""""""""

Stylistic consideration, use the plural form for collections:

* ``books`` schema has a path of "/books"
* ``book`` schema has a path of "/books/items/{id}"
* ``authors`` schema has a path of "/authors"
* ``author`` schema has a path of "/authors/{id}"

Collections
"""""""""""

Most RESTful interfaces provide one or more resources representing collections
of items. These collections can be recognized by one or more of
the following traits:

1. Using a custom tag ("tags: {collection: true}")
2. The response object has an "items" property which has an array type
3. The response array items define an "instances" relation

This guideline provides recommendations for collection resources, to provide
common functionality for manipulating elements and retrieving collection
information.

Reading & Paging
''''''''''''''''

To load the collection resource the client MUST send a GET request to the resource URI::

    => GET /api/bookstore/1.0/books

    <= HTTP 200 OK

    {
        "items": [
            { ... },
            { ... },
            ...
            { ... }
        ]
    }

A collection resource MAY support additional parameters such as:

1. ``limit={N}`` : maximum number of items in the "items" array
2. ``offset={N}`` : tells the server to skip N items
3. ``sortby={fields}`` : orders the items in the response according to the
   specified field/fields
4. ``sort={directions}`` : sorting direction - 'asc' or 'desc' (if sorting
   on multiple fields, number of specifiers must match the number of fields)

The response schema MAY be extended with a "meta" property which is an object
containing additional properties to aid the clients. For example:

1. ``total: integer`` : total number of items on the server
   (regardless of the limit/offset values)
2. ``count: integer`` : size of the "items" collection
3. ``offset: integer`` : offset used in the request
4. ``next_offset: integer`` and ``prev_offset: integer`` : offset of the
   next/previous page in a paged collection, which can be used in the
   ``next``/``prev`` links in the resource definition

.. note::

    There is still considerable debate over the exact structure
    of the "meta" object.

If the resource does return the information specified for the "meta"
property, its SHOULD use the "meta" property and the property names
documented above.  A resource MAY choose to support only some meta fields,
or to not support a "meta" section at all.

Example:

.. code-block:: yaml

    resources:
       books:
          type: object
          additionalProperties: False
          required: [items]
          properties:
             items:
                type: array
                items:
                   $ref: '#/resources/book'
             meta:
                type: object
                readOnly: True
                additionalProperties: False
                properties:
                   offset: { type: integer }
                   limit: { type: integer }
                   total: { type: integer }
                   count: { type: integer }
                   next_offset: { type: integer }
                   prev_offset: { type: integer }
          relations:
             next_page:
                resource: '#/resources/books'
                vars:
                   offset: '0/meta/next_offset'
                   limit:  '0/meta/limit'
             prev_page:
                resource: '#/resources/books'
                vars:
                   offset: '0/meta/prev_offset'
                   limit:  '0/meta/limit'
          links:
             self:
                path: "$/books"
                params:
                   offset: { type: number }
                   limit: { type: number }

::

    => GET /api/bookstore/1.0/books?limit=5&offset=10&sortby=title&sort=asc
    <= HTTP 200 OK

    {
        "items": [
            { ... },
            { ... },
            { ... },
            { ... },
            { ... }
        ],
        "meta": {
            "total": 1974,
            "count": 5,
            "offset": 10,
            "next_offset": 15,
            "prev_offset": 5
        }
    }

Creating
''''''''

To create an element in a collection the client SHOULD POST the creation data to the collection URI.

::

    => POST /api/bookstore/1.0/books
    {
        "title": "YUI Cookbook",
        "isbn": "1449304192"
    }

    <= HTTP 201 Created
    Location: /api/bookstore/1.0/books/items/1975

The server MUST reply with a 201 code and a ``Location`` header referring to
the URI of the created resource. The server MAY also return a representation
of the created resource.

.. note::

    Currently Location headers are not supported by either Lumberjack or
    sleepwalker, and reschema has no way to enforce anything about them.
    In effect, it is not really behaving as a MUST condition at this time.
    Need bugs filed on this.

Deleting
''''''''

To delete a collection element simply send a DELETE request on the resource URI:

::

    => DELETE /api/bookstore/1.0/books/items/1975
    <= HTTP 204 No Content

    => GET /api/bookstore/1.0/books/items/1975
    <= HTTP 404 Not Found

Updating
''''''''

To update a collection element, the client SHOULD send a PUT request on an
element URI with a body containing full resource representation. The server
MAY reply with an updated resource representation (which may contain
updated read-only fields).  If no resource representation is desired due
to concerns such as performance issues with large resources,
the resource MUST return a 204.

::

    => PUT /api/bookstore/1.0/books/items/1975
    {
        "title": "YUI3 Cookbook",
        "isbn": "1449304192"
    }

    <= HTTP 200 OK
    {
        "title": "YUI3 Cookbook",
        "isbn": "1449304192"
    }

Example: Bookstore
---------------------

Consider a simple REST API that provides access to a bookstore's inventory.

The ``service definition`` that describes this API: `bookstore.yaml <https://gitlab.lab.nbttech.com/steelscript/reschema/blob/master/examples/bookstore.yaml>`_

This example demonstrates most of the capabilities of both the ``service definition`` schema
as well as JSON Schema itself:

* Defines schemas, resources, methods, errors, and tasks
* Leverages schemas by "$ref"
* Examples and tasks by reference to external files
* Field constraints: limits, patterns, enumerations

Appendix: JSON Pointers
-----------------------

`RFC 7901 <http://tools.ietf.org/html/rfc6901>`_ defines JSON Pointer notation
which allows indexing into an arbitrary JSON object via a string.  The
basic syntax looks very much like traversing a directory structure, using
"/" as a delimiter.

Consider the following JSON data:

.. code-block:: json

    {
       "id": 1,
       "name": {
          "first": "John",
          "last": Doe
       },
       "age": 42,
       "children" : [
          { "first": "Susan",
            "age": 4 },
          { "first": "Bob",
            "age": 10 }
       ]
    }

The following table shows a few JSON Pointers and the resulting data:

.. list-table::
   :header-rows: 1

   - * JSON Pointer
     * Result
   - * ""
     * ``{ 'id': 1 .... }`` (The entire data structure)
   - * '/id'
     * ``1``
   - * '/name'
     * ``{ "first": "John", "last": "Doe" }``
   - * '/name/first'
     * ``"John"``
   - * '/children/0/first'
     * ``"Susan"``
   - * '/children/1/age'
     * ``10``

Appendix Relative JSON Pointers
-------------------------------

Relative JSON pointers
`IETF draft <http://datatracker.ietf.org/doc/draft-luff-relative-json-pointer/>`_
allows starting at some arbitrary point in JSON data and then
indexing to some other point in that same data.

The basic syntax of a relative JSON Pointer is "<scope>/<json pointer>",
where scope defines the number of levels to proceed *up* the data structure
from the current location, then follow the <json pointer> to retrieve the
instance value.

Using the directory structure notation, this is like traversing up
multiple directory levels before iterating back down.

Using the same data object as above, the following table illustrates
the result of a relative JSON pointer based up a starting location:

.. list-table::
   :header-rows: 1

   - * Starting point
     * Relative JSON Pointer
     * Result
   - * '/name/first'
     * '1'
     * ``{ 'first': 'John', 'last': 'Doe' }``
   - * '/name/first'
     * '1/last'
     * ``'Doe'``
   - * '/name/first'
     * '2/name/last'
     * ``'Doe'``
   - * '/children/0'
     * '0/first'
     * ``'Susan'``
   - * '/children/0'
     * '1/1/first'
     * ``'Bob'``

References
----------

* `JSON Schema draft 04`_

.. _JSON Schema draft 04: http://tools.ietf.org/html/draft-zyp-json-schema-04
.. _draft-ietf-appsawg-http-problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
