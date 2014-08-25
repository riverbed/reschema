.. For lack of a better starting point, copying pylint's scheme - codes starting with:
   C are convention/stylistic
   W are warnings (will cause problems under the right conditions)
   E are errors (schema will not work right)

General schema issues / naming conventions (001)
------------------------------------------------

  * **C0001**: Identifiers start with a letter, and contain only lowercase, numbers, and ``_``.  Applies to:

    * Type names
    * Resource names
    * Link names
    * Relation names
    * Values of an enum for a string field

  * **C0002**: The name of a type should not start or end with ``type``

  * **C0003**: The name of a resource should not start or end with ``resource``

  * **C0004**: The name of a link should not start or end with ``link``

  * **C0005**: A resource, type, link, or relation name must be at least 2 characters long (eg, pick a better name)

  * **C0006**: The service definition must have a valid description field, starting with a capital letter

  * **C0007**: The indentation should be 4 spaces

-------

  * **W0001**: The ``provider`` field must be set to ``riverbed``

  * **W0002**: The ``id`` field must be ``http://support.riverbed.com/apis/{name}/{version}``

  * **W0003**: The ``$schema`` field must be ``http://support.riverbed.com/apis/service_def/{version}``

  * **W0004**: the schema must have a title

  * **W0005**: ``object`` schema is missing ``additionalProperties``, assumed to be ``True``

-------

  * **E0001**: Invalid ``$ref``; the target cannot be found

  * **E0002**: Invalid required property when additional property is False


Links (100)
-----------

  * **C0100**: Standard links must not have a description field.  Standard links are: ``self``, ``get``, ``set``, ``create``, and ``delete``.

  * **C0101**: A non-standard link must have a valid description field.  Standard links are: ``self``, ``get``, ``set``, ``create``, and ``delete``.

-------

  * **W0100**: A ``get`` link cannot have a request body

  * **W0101**: A ``get`` link response must be the representation of the resource it belongs to

  * **W0102**: A ``set`` link request must be the representation of the resource it belongs to

  * **W0103**: A ``set`` link response must be null or the representation of the resource it belongs to

  * **W0104**: A ``delete`` link cannot have a request body

  * **W0105**: A ``delete`` link cannot have a response body

  * **W0106**: A ``create`` link must have a request body

  * **W0107**: A ``create`` link request must not be the same as the resource it belongs to

  * **W0108**: A ``create`` link response must not be the same as the resource it belongs to

  * **W0109**: A ``self`` link must be self-describing; the path template should be fulfilled by the representation returned via ``get``

  * **W0110**: The link cannot be resolved; the URI parameters require client input

  * **W0111**: The relation cannot be followed; the URI template for the target resource requires client input

-------

  * **E0100**: A ``get`` link must use http method GET

  * **E0101**: A ``set`` link must use http method PUT

  * **E0102**: A ``create`` link must use http method POST

  * **E0103**: A ``delete`` link must use http method DELETE

  * **E0105**: A parameter in URI template must be declared in schema properties


Types (200)
-----------

  * **C0200**: A type must have a valid description field

Thought about rule on types needing to be used by multiple resources, but that doesnt always work
(to cut down on extra type definitions)
  * linking between schemas (common types)
  * sometimes its useful when the indentation gets too long
Same goes for an unused type, although we may want that one if we have a way to suppress


Resources (300)
---------------

  * **C0300**: A resource must have a valid description field
  * **C0301**: A resource should be an object
  * **C0302**: Collection resource object should have an 'items' property
  
-------

  * **E0300**: The relation is invalid.  The specified resource cannot be found
