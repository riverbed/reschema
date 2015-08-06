JSON Schema primer
==================

Overview
--------

This document provides an quick run through ``json-schema`` as defined in
the following IETF drafts:

   * `JSON Schema draft 04 <http://tools.ietf.org/html/draft-zyp-json-schema-04>`_
   * `JSON Schema: interactive and non interactive validation <http://json-schema.org/latest/json-schema-validation.html>`_

The `GL4 <../gl4>`_ ``rest-schema`` relies heavily on JSON schemea as a way of
describing data types.  Similar to C ``struct``, at a minimum a
``json-schema`` lays out all the elements and types of a JSON object.

This representation is used to describe both simple strings and numbers as well
as complex data types in JSON.  The schema may also include documentation for
each attribute, as well as constraints on data values.

For example, the following simple ``json-schema`` defines a JSON object
representing an ``address``::

    {
        "type": "object",
        "properties" : {
            "street" : { "type": "string", "description": "Street Address" },
            "city" : { "type": "string", "description": "City" },
            "state" : { "type": "string", "description": "State", "pattern": "[A-Z][A-Z]" },
            "zip" : { "type": "string", "description": "Zip Code (5-digit)", "pattern": "[0-9][0-9][0-9][0-9][0-9]" }
        }
    }

A JSON object conforming to this schema::

    {
        "street" : "123 High Street",
        "city" : "Springfield",
        "state": "IL",
        "zip": "12345"
    }

The examples in this document are presented in YAML format rather than JSON,
as YAML is easier to read and is close enough to JSON that there is no ambiguity
in meaning.  The YAML equivalent of the above examples is shown below:

Address schema in YAML::

   type: object
   properties:
      street: { type: string, description: "Street Address" }
      city: { type: string, description: "City" }
      state: { type: string, description: "State", pattern: "[A-Z][A-Z]" }
      zip: { type: string, description: "Zip Code (5-digit)", pattern: "[0-9][0-9][0-9][0-9][0-9]" }

Address object in YAML::

   street: "123 High Street"
   city: "Springfield"
   state: "IL"
   zip: "12345"

Types
-----

type: boolean
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'boolean'
     - yes
     - Defines the data type as a boolean value
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - default
     - <number>
     - no
     - Default value if not specified

Example::

   type: boolean
   description: 'Likes chocolate'
   default: True

Note: JSON uses lowercase ``true`` and ``false``, whereas YAML uses capitalized ``True`` and ``False``.

type: number
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description*
   * - type
     - 'number
     - yes
     - Defines the data type as numeric, integer or float
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - minimum
     - <number>
     - no
     - Minimum allowed value for validation
   * - maximum
     - <number>
     - no
     - Maximum allowed value for validation
   * - exclusiveMinimum
     - <bool>
     - no
     - true if value must be strictly greater than minimum, false by default
   * - exclusiveMaximum
     - <bool>
     - no
     - true if value must be strictly less than maximum, false by default
   * - enum
     - [<number>, ...]
     - no
     - List of allowed values
   * - default
     - <number>
     - no
     - Default value if not specified

Example::

   type: number
   description: 'Length (inches)'
   minimum: 0
   maximum: 100
   exclusiveMaximum: true
   default: 3.5

type: integer
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'integer'
     - yes
     - Defines the data type as a numeric integer
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - minimum
     - <integer>
     - no
     - Minimum allowed value for validation
   * - maximum
     - <integer>
     - no
     - Maximum allowed value for validation
   * - exclusiveMinimum
     - <bool>
     - no
     - true if value must be strictly greater than minimum, false by default
   * - exclusiveMaximum
     - <bool>
     - no
     - true if value must be strictly less than maximum, false by default
   * - enum
     - [<integer>, ...]
     - no
     - List of allowed values
   * - default
     - <integer>
     - no
     - Default value if not specified

Example::

   type: integer
   description: 'Number of rabbits (up to 89)'
   minimum: 0
   maximum: 100
   default: 1
   enum: [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

type: string
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'string'
     - yes
     - Defines the data type as a string
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - minLength
     - <integer>
     - no
     - Minimum allowed length for validation
   * - maxLength
     - <integer>
     - no
     - Maximum allowed length for validation
   * - pattern
     - <regex>
     - no
     - Regular expression defining the allowed string values
   * - enum
     - [<string>, ...]
     - no
     - List of allowed values
   * - default
     - <string>
     - no
     - Default value if not specified

.. note::

   'pattern' is not anchored by default, so should include '^' and '$' as needed to anchor to the beginning or end of the value when matching

Example::

   type: string
   description: 'Color'
   default: 'red'
   enum: [ 'red', 'yellow', 'blue', 'green' ]

Example::

   type: string
   description: 'State (2 letter code)'
   minLength: 2
   maxLength: 2
   pattern: '^[A-Z][A-Z]$'

type: array
^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'array'
     - yes
     - Defines the data type as an array
   * - items
     - <json-schema>
     - yes
     - Defines the data type of the array elements
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - minItems
     - <integer>
     - no
     - Minimum number of items for validation
   * - maxItems
     - <integer>
     - no
     - Maximum number of items for validation

Example::

   type: array
   description: 'Favorite colors'
   items:
      type: string
      description: 'Color'
      enum: [ 'red', 'yellow', 'blue', 'green' ]

type: object
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'object'
     - yes
     - Defines the data type as an object
   * - description
     - <string>
     - no
     - One line description of the meaning of the value
   * - properties
     - <object>
     - no
     - key/value pairs defining possible properties and their data types
   * - additionalProperties
     - <bool> or <json-schema>
     - no
     - true or a schema if keys other than those defined in 'properties' are allowed, default true
   * - required
     - [key, ...]
     - no
     - list of property key names that must be present for validation

.. note::

   * If additionalProperties is set to true, any number of additionalProperties may be present of any data type.
   * If additionalProperties is a schema, additional properties (beyond what are defined in 'properties') are allowed and must match the schema

Example::

   type: object
   description: 'Address'
   properties:
      street: { type: string, description: "Street Address" }
      city: { type: string, description: "City" }
      state: { type: string, description: "State", pattern: "[A-Z][A-Z]" }
      zip: { type: string, description: "Zip Code (5-digit)", pattern: "[0-9][0-9][0-9][0-9][0-9]" }
   additionalProperties: false
   required: [ street, city, state, zip ]

Example: This word list object allows any number of additional properties,
expected to be words and the value for each additional property must be
a number.

::

   type: object
   description: 'Word list and count of occurrences'
   additionalProperties:
      type: number
      description: "count of occurences of each word"

Valid value for the above word list schema::

   one: 5
   the: 10
   fox: 1
   quick: 1
   a: 5

type: null
^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - property
     - value
     - required
     - description
   * - type
     - 'null'
     - yes
     - Defines the data type as a null value
   * - description
     - <string>
     - no
     - One line description of the meaning of the value

The null value is typically used in combination with another type to allow
a value to be null.

Example::

   type: null
   description: 'The Null value'

More comprehensive example with a string type::

   anyOf:
      -  type: null
      -  type: string
   description: 'A string or a null'

References via $ref
-------------------

The '$ref' keyword may be used to reference another schema defined elsewhere.
This may be used anywhere a ``json-schema`` definition is required.

The syntax of a fully qualified reference is a full URI that points to
a JSON document with a fragment that is a JSON pointer to some
JSON schema within that document.

There are three supported formats of the reference, which mirrors standard
URL page resolution:

.. list-table::

   * - *Local*
     -  #{jsonpointer}
     - Relative to the same JSON document as the $ref
   * - *Server*
     - /{name}/{version}#{jsonpointer}
     - Relative to another JSON document on the same server
   * - *Full*
     - {uri}#{jsonpointer}
     - Fully qualified reference

Example: 'full_name' schema, located within a JSON document available at
"http://support.riverbed.com/apis/types/1.0" (example URL only).

::

    types:
       full_name:
          type: object
          description: 'Full name'
          additionalProperties: false
          properties:
             first: { type: string }
             last: { type: string }

Referencing the ``full_name`` schema from within the same JSON document uses
the *local* format::

   type: array
   description: 'List of friends'
   items:
      $ref: '#/types/full_name'

A fully qualified reference adds the full URI::

   type: array
   description: 'List of friends'
   items:
      $ref: 'http://support.riverbed.com/apis/types/1.0#/types/full_name'

Note that it is possible, to reference other schemas such as ``first``::

   type: array
   description: 'All first names'
   items:
      $ref: 'http://support.riverbed.com/apis/types/1.0#/types/full_name/properties/first'

Composite types
---------------

anyOf
^^^^^

The ``anyOf`` keyword takes an array of schemas as a value and may be combined
with other composite types as well as a base ``type``.  An instance is
valid according to the anyOf set if one or more of the schemas is in turn valid.

Example with no base type allowing an instance to be eiother a string or
a number::

   description: 'String or number'
   anyOf:
      -  type: string
      -  type: number

Example with a base type of a number and using anyOf for validation::

   type: number
   description: 'Number 1-10 or 50-100'
   anyOf:
      -  type: number
         minimum: 1
         maximum: 10
      -  type: number
         minimum: 50
         maximum: 100

allOf
^^^^^

The ``allOf`` keyword is similar to ``anyOf`` except that an instance is
valid if and only if all schemas are valid:

Example::

   type: number
   description: "Number between 1 and 100 but not 50-60"

   allOf:
      -  minimum: 1
         maximum: 100
      -  not:
            minimum: 50
            maximum: 60

oneOf
^^^^^

The ``oneOf`` keyword is similar to ``anyOf`` except that an instance is
valid if and only if all exactly one of the schemas is valid and all others
are *not* valid.

Example::

   type: object
   description: "If a1, then b is 5-10, if a2, then b is 50-100"
   additionalProperties: False
   properties:
      a1: { type: number }
      a2: { type: number }
      b:  { type: number }

   oneOf:
      -  type: object
         required: [a1, b]
         properties:
            b:
               type: number
               minimum: 5
               maximum: 10

      -  type: object
         required: [a2, b]
         properties:
            b:
               type: number
               minimum: 50
               maximum: 100

not
^^^

The ``not`` keyword takes a single schema as an argument.  An instance is
valid only if the schema does *not* validate successfully.  The schema may
in turn be a schema using ``anyOf``, ``allOf``, or ``oneOf`` to create arbitrary
boolean validation logic.

Example::

   type: number
   description: "Number less than 5 and greater than 10"
   not:
      type: number
      minimum: 5
      maximum: 10

More complex example nesting with anyOf::

   type: number
   description: "Any number not between 5-10 and 50-100"
   not:
      anyOf:
         -  type: number
            minimum: 5
            maximum: 10

         -  type: number
            minimum: 50
            maximum: 100
