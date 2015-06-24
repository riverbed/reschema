# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import print_function

import re
import uritemplate
import traceback
import reschema.exceptions
import reschema.settings
from reschema import jsonschema

INDENT_OFFSET = 4

reschema.settings.LOAD_DESCRIPTIONS = True
reschema.settings.MARKED_LOAD = True


def get_first_marked_object(*objects):
    """ Given a list of objects, return the first that has marks.
    :param objects: A number of objects to check for.
    :returns: The first member of objects with a "start_mark" attribute or None

    """
    for obj in objects:
        if hasattr(obj, "start_mark"):
            return obj


class ValidationFail(reschema.exceptions.MarkedError):
    """
    Schema did something it shouldn't have
    """
    pass


class RuleDisabled(Exception):
    """
    Rule is disabled due to a relint-disable tag
    """
    pass


class Rule(object):
    """
    Base class for a rule validator.  Exists mainly to isolate the validation
    callback from the code which checks for relint-disable tags in the
    servicedef.
    """

    def __init__(self, rule_id, rule_func):
        """
        :param rule_id: Rule's Id, for disabling/reporting purposes
        :param rule_func: Rule validation callback
        """

        self.rule_id = rule_id
        self._rule_func = rule_func

    def __call__(self, schema, disabled):
        """
        Run the rule

        :param schema: schema to verify
        :type: reschema.jsonschema.Schema or derived
               reschema.jsonschema.Link or
               reschema.jsonschema.Relation or
               reschema.servicedef.ServiceDef

        :param disabled: list of disabled rules
        """

        if self.rule_id in disabled:
            raise RuleDisabled

        self._rule_func(schema)


class Result(object):
    """ Helper to hold the result of a rule execution """

    PASSED = 0
    FAILED = 1
    DISABLED = 2

    def __init__(self, rule_id, obj_id, status, message='', exc=None):
        """
        :param rule_id: Rule that executed
        :param obj_id: Object checked (in json-pointer format)
        :param status: PASSED/FAILED/DISABLED
        :param message: Optional additional information
        :param exc: Optional exception that was raised to cause this Result.

        """

        self.rule_id = rule_id
        self.obj_id = obj_id
        self.status = status
        self.message = message
        self.exc = exc

    def __str__(self):
        status = ['PASS', 'FAIL', 'DIS '][self.status]

        # marks are easier to find in the document than the ID.
        if self.exc and self.exc.start_mark:
            return ('{name}:{line}:{column}: {status} [{rule}]  '
                    '{message}').format(name=self.exc.start_mark.name,
                                        line=self.exc.start_mark.line + 1,
                                        column=self.exc.start_mark.column + 1,
                                        status=status,
                                        rule=self.rule_id,
                                        message=self.message)
        return '{0}: [{1}] - \'{2}\' {3}'.format(status, self.rule_id,
                                                 self.obj_id, self.message)


class Validator(object):
    """
    Class which collects rules and executes them, tracking pass/fail/etc
    """

    SERVICEDEF_RULES = []
    TYPE_RULES = []
    RESOURCE_RULES = []
    LINK_RULES = []
    SCHEMA_RULES = []
    VERBOSITY = 0
    RVBD_BASE_URL = 'http://support.riverbed.com/apis'
    STD_LINKS = ['self', 'get', 'set', 'delete', 'create']

    @classmethod
    def servicedef(cls, rule_id):
        """ Registers a rule which operates on the servicedef """
        def wrapper(rule_func):
            rule = Rule(rule_id, rule_func)
            cls.SERVICEDEF_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def typedef(cls, rule_id):
        """ Registers a rule which operates on a type """
        def wrapper(rule_func):
            rule = Rule(rule_id, rule_func)
            cls.TYPE_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def resource(cls, rule_id):
        """ Registers a rule which operates on a resource """
        def wrapper(rule_func):
            rule = Rule(rule_id, rule_func)
            cls.RESOURCE_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def link(cls, rule_id):
        """ Registers a rule which operates on a link """
        def wrapper(rule_func):
            rule = Rule(rule_id, rule_func)
            cls.LINK_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def schema(cls, rule_id):
        def wrapper(rule_func):
            rule = Rule(rule_id, rule_func)
            cls.SCHEMA_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def set_verbosity(cls, level):
        cls.VERBOSITY = level

    def check_schema(self, schema, results, disabled_rules_above):
        """
        Report any failures defined within a schema, including
        top-level failures as well as any failures in each subschema
        """
        if type(schema) is not jsonschema.Ref:
            rules = get_disabled(schema)
            disabled_rules = disabled_rules_above.union(rules)

            results.extend(self._run_rules(Validator.TYPE_RULES +
                                           Validator.SCHEMA_RULES,
                                           schema, disabled_rules))

            self.check_sub_schema(schema, results, disabled_rules)

    def check_sub_schema(self, schema, results, disabled_rules):
        """
        Check if any subschema defined within schema is valid.
        In particular, find any possible existing keywords and
        check individual subschema defined underneath the keyword.
        """
        if hasattr(schema, 'properties'):
            for _, prop in schema.properties.iteritems():
                self.check_schema(prop, results, disabled_rules)

        if hasattr(schema, 'items'):
            self.check_schema(schema.items, results, disabled_rules)

        if hasattr(schema, '_request') and schema._request is not None:
            if type(schema._request) not in [jsonschema.Ref, jsonschema.Null]:
                self.check_schema(schema._request, results, disabled_rules)

        if hasattr(schema, '_response') and schema._response is not None:
            if type(schema._response) not in [jsonschema.Ref, jsonschema.Null]:
                self.check_schema(schema._response, results, disabled_rules)

        if hasattr(schema, 'anyof'):
            for subschema in schema.anyof:
                self.check_schema(subschema, results, disabled_rules)

        if hasattr(schema, 'oneof'):
            for subschema in schema.oneof:
                self.check_schema(subschema, results, disabled_rules)

        if hasattr(schema, 'allof'):
            for subschema in schema.allof:
                self.check_schema(subschema, results, disabled_rules)

        if hasattr(schema, 'not_') and schema.not_ is not None:
            self.check_schema(schema.not_, results, disabled_rules)

        if hasattr(schema, '_params'):
            for _, param in schema._params.iteritems():
                self.check_schema(param, results, disabled_rules)

        if (isinstance(schema, jsonschema.Merge)):
            self.check_schema(schema.refschema, results, disabled_rules)

        if hasattr(schema, 'relations') and len(schema.relations) > 0:
            for relation in schema.relations.items():
                # relation[1] is type of jsonschema.Relation
                self.check_schema(relation[1], results, disabled_rules)

        return results

    def run(self, sdef):
        """
        Run validation against the servicedef.
        :param sdef: service definition to run against
        :type sdef: reschema.servicedef.ServiceDef

        :return: A list of Result objects
        """

        results = []

        print('Checking top-level schema correctness')
        sdef_disabled = get_disabled(sdef)
        results.extend(self._run_rules(Validator.SERVICEDEF_RULES, sdef,
                                       sdef_disabled))

        print('Checking types')
        for typedef in sdef.type_iter():
            if type(typedef) is not jsonschema.Ref:
                typedef_disabled = get_disabled(typedef).union(sdef_disabled)
                results.extend(self._run_rules(Validator.TYPE_RULES +
                                               Validator.SCHEMA_RULES,
                                               typedef, typedef_disabled))
                self.check_sub_schema(typedef, results, typedef_disabled)

        print('Checking resources')
        for resource in sdef.resource_iter():
            if type(resource) is not jsonschema.Ref:
                resource_disabled = get_disabled(resource).union(sdef_disabled)
                results.extend(self._run_rules(Validator.RESOURCE_RULES +
                                               Validator.SCHEMA_RULES,
                                               resource, resource_disabled))

                self.check_sub_schema(resource, results, resource_disabled)

            if self.VERBOSITY > 1:
                print('Checking links for \'{}\''.format(resource.name))

            for _, link in resource.links.items():
                if type(link) is not jsonschema.Ref:
                    link_disabled = get_disabled(link).union(resource_disabled)
                    results.extend(self._run_rules(Validator.LINK_RULES +
                                                   Validator.SCHEMA_RULES,
                                                   link, link_disabled))
                    self.check_sub_schema(link, results, link_disabled)
        return results

    def _run_rules(self, rules, obj, disabled_rules):
        """
        Runs a block of rules on a schema object

        :param rules: List of rules to run
        :param obj: reschema object to run the rules on

        :return: List of Result objects
        """

        results = []
        for rule in rules:
            try:
                rule(obj, disabled_rules)
                result = Result(rule.rule_id, obj.id, Result.PASSED)

            except ValidationFail as exc:
                result = Result(rule.rule_id, obj.id, Result.FAILED,
                                exc.message, exc)

            except RuleDisabled:
                result = Result(rule.rule_id, obj.id, Result.DISABLED)

            if (result.status != Result.PASSED) or (self.VERBOSITY > 1):
                print(str(result))

            results.append(result)

        return results


def get_disabled(obj):
    """
    Obtain the top-level disabled rules as well as on the object

    :param: schema object to get disabled rules from
    :type: reschema.jsonschema.Relation or
           reschema.jsonschema.Object or
           reschema.jsonschema.Link or
           reschema.servicedef.ServiceDef

    :returns: set of disabled rules of the object
    """
    return set(obj.tags.get('relint-disable', []))


def lint(sdef, filename):
    """
    Performs all checks on a loaded service definition.

    :param sdef:
    :type sdef: reschema.servicedef.ServiceDef

    :param filename:
    :type string: the absolute name of the processing yml file

    :returns: total number of failures
    """

    validator = Validator()
    results = validator.run(sdef)

    failures = len([r for r in results if r.status == Result.FAILED])

    # TODO: load cross-referenced schemas
    print('Checking referenced types and resources')
    errors = sdef.check_references()
    xref_failures = 0
    if errors:
        for error in errors:
            print('FAIL: [E0001] - \'{0}\' cannot be resolved'
                  .format(error.id))
        xref_failures += len(errors)

    errors = check_indentation(filename)
    indent_failures = len(errors)
    for row, col in errors:
        print ("{0}:{1}:{2} FAIL: [C0007] - indentation should be {3} spaces"
               .format(filename, row, col, INDENT_OFFSET))

    return xref_failures + failures + indent_failures


def first_char_pos(line):
    """
    return the indentation of first non-space character of the line
    If the first char is # or none such char exists, return False
    """
    striped_line = str.lstrip(line)
    if len(striped_line) == 0 or striped_line[0] == '#':
        return -1
    return len(line) - len(striped_line)


def check_indentation(filename):
    """
    check if each indentation is 4 spaces, otherwise generate issue C0007
    rule: when the first non-whitespace character is '#', ignore.
          otherwise, the indentation of the first valid char is deeper
          than the previous indentation, then the delta must be 4 spaces
    """
    try:
        with open(filename, 'r') as f:
            list = f.read().split('\n')
            ind = 0

            while ind < len(list) and first_char_pos(list[ind]) == -1:
                ind += 1
            pre_pos = first_char_pos(list[ind])
            curr_pos = 0
            errors = []
            while ind < len(list):
                curr_pos = first_char_pos(list[ind])
                ind += 1
                if curr_pos == -1:
                    continue
                if not (curr_pos == pre_pos or
                        curr_pos == pre_pos + INDENT_OFFSET or
                        (pre_pos > curr_pos and
                         (pre_pos - curr_pos) % INDENT_OFFSET == 0)):
                    errors.append((ind, curr_pos))
                pre_pos = curr_pos
            return errors
    except:
        print ("Function check_indentation failed, Exception: {0}"
               .format(traceback.format_exc()))
        return []


def check_valid_identifier(name, location):
    """
    Check that an identifier (link name, resource name, etc) is valid
    """
    if not re.match('^[a-z0-9_]*$', name):
        msg = "'{0}' contains invalid characters (only a-z, 0-9, _)"
        raise ValidationFail(msg.format(location), name)

    if not re.match('^[a-z]', name):
        msg = "'{0}' does not start with a letter"
        raise ValidationFail(msg.format(location), name)


def check_name_length(name, location):
    """
    Check that a name is at least 2 characters long and contain a vowel
    """
    if len(name) < 2:
        raise ValidationFail(
            "'{0}' should be at least 2 characters long".format(location.id),
            name)


def check_valid_description(text, location, obj=None, required=True):
    """
    Checks the text of a description
    """
    if not text and required:
        raise ValidationFail("'{0}' has no description field".format(location),
                             obj)

    if not text[0].isupper():
        msg = "'{0}' description does not begin with uppercase character"
        raise ValidationFail(msg.format(location), text)


@Validator.servicedef('W0001')
def schema_provider_valid(sdef):
    if sdef.provider != 'riverbed':
        raise ValidationFail("'provider' field must be 'riverbed'",
                             sdef.provider)


@Validator.servicedef('W0002')
def schema_id_valid(sdef):
    id_re = Validator.RVBD_BASE_URL + '/([a-z0-9_.]+)/([0-9](.[0-9]){1,2})$'
    match = re.match(id_re, sdef.id)
    if not match:
        msg = "'id' must be '{0}/<name>/<version>'"
        raise ValidationFail(msg.format(Validator.RVBD_BASE_URL), sdef.id)
    name = match.group(1)
    if name != sdef.name:
        msg = "schema id does not match the schema name: '{0}'"
        raise ValidationFail(msg.format(sdef.name), sdef.id)
    version = match.group(2)
    if version != sdef.version:
        msg = "schema id does not match the schema version: '{0}'"
        raise ValidationFail(msg.format(sdef.version), sdef.id)


@Validator.servicedef('W0003')
def schema_field_valid(sdef):
    schema_re = Validator.RVBD_BASE_URL + '/service_def/([0-9](.[0-9]){1,2})$'
    match = re.match(schema_re, sdef.schema)
    if not match:
        msg = "'$schema' field must be '{0}/service_def/<version>'"
        raise ValidationFail(msg.format(Validator.RVBD_BASE_URL), sdef.schema)


@Validator.servicedef('W0004')
def schema_has_title(sdef):
    if not sdef.title:
        raise ValidationFail("the schema must have a title", sdef)


@Validator.schema('W0005')
def schema_has_additional_properties(schema):
    if isinstance(schema, jsonschema.Object):
        if 'additionalProperties' not in schema.input:
            raise ValidationFail("additionalProperties missing in '{0}'"
                                 .format(schema.id), schema.name)


@Validator.schema('W0006')
def required_property_with_default_value(schema):
    if hasattr(schema, 'required') and schema.required:
        for required_prop in schema.required:
            if required_prop in schema.properties:
                default = getattr(schema.properties[required_prop], 'default',
                                  None)
                if default is not None:
                    raise ValidationFail(
                        "A required property '{0}' should not have a default "
                        "value in '{1}'".format(
                            required_prop, schema.fullname()
                        ),
                        default)


@Validator.schema('C0001')
def schema_has_valid_name(schema):
    # introducing the below logic because schemas underneath any/one/allof
    # are with names as any/one/allOf[*], where * is a non-negative int
    # for those schema object, we do not want to generate C0001 failures
    if hasattr(schema, 'parent') and hasattr(schema.parent, 'input'):
        keys = schema.parent.input.keys()
        if set(['anyOf', 'oneOf', 'allOf']) & set(keys):
            return

    check_valid_identifier(schema.name, schema.id)


@Validator.typedef('C0002')
def type_does_not_have_prefix_or_suffix(typedef):
    # Some people suffix or prefix the name with type, not needed with the
    # 2.1 $ref: #/types syntax
    type_lc = typedef.name.lower()
    if type_lc.startswith('type'):
        raise ValidationFail(
            "'{0}' should not start with 'type'".format(typedef.id),
            typedef.name)
    elif type_lc.endswith('type'):
        raise ValidationFail(
            "'{0}' should not end with 'type'".format(typedef.id),
            typedef.name)


@Validator.resource('C0003')
def resource_does_not_have_prefix_or_suffix(resource):
    res_lc = resource.name.lower()
    if res_lc.startswith('resource'):
        raise ValidationFail(
            "'{0}' should not start with 'resource'".format(resource.id),
            resource.name)
    elif res_lc.endswith('resource'):
        raise ValidationFail(
            "'{0}' should not end with 'resource'".format(resource.id),
            resource.name)


@Validator.link('C0004')
def link_does_not_have_prefix_or_suffix(link):
    link_lc = link.name.lower()
    if link_lc.startswith('link'):
        raise ValidationFail(
            "'{0}' should not start with 'link'".format(link.id),
            link.name)
    elif link_lc.endswith('link'):
        raise ValidationFail(
            "'{0}' should not end with 'link'".format(link.id),
            link.name)


@Validator.schema('C0005')
def schema_name_check_length(schema):
    check_name_length(schema.name, schema)


@Validator.servicedef('C0006')
def sd_has_valid_description(sdef):
    check_valid_description(sdef.description, 'ServiceDef', sdef,
                            required=True)


@Validator.link('C0100')
def link_std_has_no_description(link):
    if link.name in Validator.STD_LINKS and link.description:
        raise ValidationFail(
            "'{0}' link must have no description".format(link.name),
            link.description)


@Validator.link('C0101')
def link_non_std_has_description(link):
    if link.name not in Validator.STD_LINKS:
        check_valid_description(link.description, link.id, link, required=True)


@Validator.link('W0100')
def link_get_has_no_request_body(link):
    if 'get' == link.name and 'null' != link.request.typestr:
        obj = get_first_marked_object(link._request, link.name)
        raise ValidationFail("'get' link cannot have a request body", obj)


@Validator.link('W0101')
def link_get_response_is_the_resource(link):
    if 'get' == link.name and link.schema.id != link.response.id:
        obj = get_first_marked_object(link._response, link.name)
        raise ValidationFail(
            "'get' link response must be '{0}' ".format(link.schema.id),
            obj)


@Validator.link('W0102')
def link_set_request_is_the_resource(link):
    if 'set' == link.name and link.schema.id != link.request.id:
        obj = get_first_marked_object(link._request, link.name)
        raise ValidationFail(
            "'set' link request must be '{0}' ".format(link.schema.id),
            obj)


@Validator.link('W0103')
def link_set_response_is_null_or_resource(link):
    if ('set' == link.name and
            'null' != link.response.typestr and
            link.schema.id != link.response.id):
        obj = get_first_marked_object(link._response, link.name)
        msg = "'set' link response must be empty or '{0}'"
        raise ValidationFail(msg.format(link.schema.id), obj)


@Validator.link('W0104')
def link_delete_has_no_request_body(link):
    if 'delete' == link.name and 'null' != link.request.typestr:
        obj = get_first_marked_object(link._request, link.name)
        raise ValidationFail("'delete' link cannot have a request body", obj)


@Validator.link('W0105')
def link_delete_has_no_response_body(link):
    if 'delete' == link.name and 'null' != link.response.typestr:
        obj = get_first_marked_object(link._response, link.name)
        raise ValidationFail("'delete' link cannot have a response body", obj)


@Validator.link('W0106')
def link_create_has_request_body(link):
    if 'create' == link.name and 'null' == link.request.typestr:
        raise ValidationFail("'create' link must have a request body",
                             link.name)


@Validator.link('W0107')
def link_create_request_is_not_resource(link):
    if 'create' == link.name and link.schema.id == link.request.id:
        raise ValidationFail(
            "'create' request must not be '{0}'".format(link.schema.id),
            link._request)


@Validator.link('W0108')
def link_create_response_is_not_resource(link):
    if 'create' == link.name and link.schema.id == link.response.id:
        raise ValidationFail(
            "'create' response must not be '{0}'".format(link.schema.id),
            link._response)


@Validator.link('W0112')
def link_path_does_not_end_in_slash(link):
    if link.path:
        pathstr = str(link.path)
        if pathstr.endswith('/') and pathstr != '/':
            raise ValidationFail("A link path must not end with /", link.path)


@Validator.link('E0100')
def link_get_method_is_get(link):
    if 'get' == link.name and 'GET' != link.method.upper():
        raise ValidationFail("'get' link must use http method GET",
                             link.method)


@Validator.link('E0101')
def link_set_method_is_put(link):
    if 'set' == link.name and 'PUT' != link.method.upper():
        raise ValidationFail("'set' link must use http method PUT",
                             link.method)


@Validator.link('E0102')
def link_create_method_is_post(link):
    if 'create' == link.name and 'POST' != link.method.upper():
        raise ValidationFail("'create' link must use http method POST",
                             link.method)


@Validator.link('E0103')
def link_delete_method_is_delete(link):
    if 'delete' == link.name and 'DELETE' != link.method.upper():
        raise ValidationFail("'delete' link must use http method DELETE",
                             link.method)


@Validator.resource('C0300')
def resource_has_valid_description(resource):
    check_valid_description(resource.description, resource.id, resource,
                            required=True)


@Validator.resource('C0301')
def resource_type_is_object(resource):
    # NOTE: relint does not load referenced files yet.
    if resource.is_ref():
        print("Referenced schema not validated: '{0}'".format(
              resource.refschema.fullid()))
        return
    if 'object' != resource.typestr:
        raise ValidationFail(
            "resource '{0}' should be an object".format(resource.name),
            resource)


@Validator.typedef('C0200')
def type_has_valid_description(typedef):
    check_valid_description(typedef.description, typedef.id, typedef,
                            required=True)


@Validator.schema('E0002')
def required_is_valid(schema):
    if (hasattr(schema, 'required') and hasattr(schema, 'properties')
            and hasattr(schema, 'additional_properties')):
        if (schema.additional_properties is False and
                schema.required is not None):
            for k in schema.required:
                if k not in schema.properties:
                    raise ValidationFail("Required field '{0}' is not"
                                         " defined in '{1}'"
                                         .format(k, schema.fullname()), k)


@Validator.schema('E0003')
def relation_is_valid(schema):
    if isinstance(schema, jsonschema.Relation):
        try:
            schema.resource
        except jsonschema.InvalidReference:
            raise ValidationFail("Invalid relation '{0}': '{1}' not found".
                                 format(schema.fullname(),
                                        schema._resource_id), schema.name)


@Validator.link('E0105')
def link_uritemplate_param_declared(link):
    params = uritemplate.variables(link.path.template)
    for param in params:
        if link.schema.typestr != 'object':
            msg = ("The resource '{0}' is not an object, "
                   "so the parameter '{1}' in the uritemplate "
                   "'{2}' is not declared in link '{3}'")
            raise ValidationFail(
                msg.format(link.schema.fullname(), param, link.path.template,
                           link.name),
                link)
        elif param not in link.schema.properties:
            msg = ("The parameter '{0}' in the uritemplate '{1}'"
                   " in link '{2}' is not declared in properties"
                   " in resouce '{3}'")
            raise ValidationFail(
                msg.format(param, link.path.template, link.name,
                           link.schema.fullname()),
                link)


@Validator.resource('C0303')
def self_link_is_first(resource):
    if 'self' not in resource.links:
        return

    self_mark = resource.links['self'].name.start_mark
    for link in resource.links.values():
        mark = link.name.start_mark
        if link.name == "self":
            continue
        if (mark.line, mark.column) < (self_mark.line, self_mark.column):
            msg = "'self' link should be the first in '{0}'"
            raise ValidationFail(
                msg.format(resource.fullname()),
                resource.links['self'].name
            )
