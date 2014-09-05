# Copyright (c) 2014 Riverbed Technology, Inc.

from __future__ import print_function

import re
import uritemplate
import traceback

from reschema.jsonschema import Merge, InvalidReference, Relation, Ref, Null


class ValidationFail(Exception):
    """
    Schema did something it shouldn't have
    """
    pass


class RuleDisabled(Exception):
    """
    Rule is disabled due to a relint-disable tag
    """
    pass


class RuleBase(object):
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


class ServicedefRule(RuleBase):
    """
    Wrapper for a rule validating the top-level servicedef information
    """

    def __call__(self, sdef):
        """
        Run the rule

        :param sdef: servicedef to verify
        :type sdef: reschema.servicedef.ServiceDef
        """

        if self.rule_id in sdef.tags.get('relint-disable', []):
            raise RuleDisabled

        self._rule_func(sdef)


class TypeRule(RuleBase):
    """
    Wrapper for a rule validating a type definition
    """

    def __call__(self, typedef):
        """
        Run the rule

        :param typedef: typedef to verify
        :type typedef: reschema.jsonschema.Schema or derived
        """

        # Grab the disabled rules from the typedef and the servicedef
        disabled = (typedef.tags.get('relint-disable', []) +
                    typedef.servicedef.tags.get('relint-disable', []))

        if self.rule_id in disabled:
            raise RuleDisabled

        self._rule_func(typedef)


class ResourceRule(RuleBase):
    """
    Wrapper for a rule validating a resource
    """

    def __call__(self, resource):
        """
        Run the rule

        :param resource: resource to verify
        :type resource: reschema.jsonschema.Schema or derived
        """

        # Grab the disabled rules from the typedef and the servicedef
        disabled = (resource.tags.get('relint-disable', []) +
                    resource.servicedef.tags.get('relint-disable', []))

        if self.rule_id in disabled:
            raise RuleDisabled

        self._rule_func(resource)


class SchemaRule(RuleBase):
    """
    Wrapper for a rule validating a schema definition
    """

    def __call__(self, schema):
        """
        Run the rule

        :param schema: schema to verify
        :type schema: reschema.jsonschema.Schema or derived
        """
        # Grab the disabled rules from the typedef and the servicedef
        disabled = (schema.tags.get('relint-disable', []) +
                    schema.servicedef.tags.get('relint-disable', []))

        if self.rule_id in disabled:
            raise RuleDisabled

        return self._rule_func(schema)


class LinkRule(RuleBase):
    """
    Wrapper for a rule validating a link
    """

    def __call__(self, link):
        """
        Run the rule

        :param typedef: typedef to verify
        :type typedef: reschema.jsonschema.Link
        """

        # Grab the disabled rules from the link, resource, and the servicedef
        disabled = (link.tags.get('relint-disable', []) +
                    link.schema.tags.get('relint-disable', []) +
                    link.servicedef.tags.get('relint-disable', []))

        if self.rule_id in disabled:
            raise RuleDisabled

        self._rule_func(link)


class Result(object):
    """ Helper to hold the result of a rule execution """

    PASSED = 0
    FAILED = 1
    DISABLED = 2

    def __init__(self, rule_id, obj_id, status, message=''):
        """
        :param rule_id: Rule that executed
        :param obj_id: Object checked (in json-pointer format)
        :param status: PASSED/FAILED/DISABLED
        :param message: Optional additional information
        """

        self.rule_id = rule_id
        self.obj_id = obj_id
        self.status = status
        self.message = message

    def __str__(self):
        status = ['PASS', 'FAIL', 'DIS '][self.status]

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
            rule = ServicedefRule(rule_id, rule_func)
            cls.SERVICEDEF_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def typedef(cls, rule_id):
        """ Registers a rule which operates on a type """
        def wrapper(rule_func):
            rule = TypeRule(rule_id, rule_func)
            cls.TYPE_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def resource(cls, rule_id):
        """ Registers a rule which operates on a resource """
        def wrapper(rule_func):
            rule = ResourceRule(rule_id, rule_func)
            cls.RESOURCE_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def link(cls, rule_id):
        """ Registers a rule which operates on a link """
        def wrapper(rule_func):
            rule = LinkRule(rule_id, rule_func)
            cls.LINK_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def schema(cls, rule_id):
        def wrapper(rule_func):
            rule = SchemaRule(rule_id, rule_func)
            cls.SCHEMA_RULES.append(rule)

            return rule
        return wrapper

    @classmethod
    def set_verbosity(cls, level):
        cls.VERBOSITY = level

    def check_schema(self, schema, results):
        """
        Report any failures defined within a schema, including
        top-level failures as well as any failures in each subschema
        """
        if type(schema) is not Ref:
            results.extend(self._run_rules(Validator.TYPE_RULES +
                                           Validator.SCHEMA_RULES, schema))
            self.check_sub_schema(schema, results)

    def check_sub_schema(self, schema, results):
        """
        Check if any subschema defined within schema is valid.
        In particular, find any possible existing keywords and
        check individual subschema defined underneath the keyword.
        """
        if hasattr(schema, 'properties'):
            for _, prop in schema.properties.iteritems():
                self.check_schema(prop, results)

        if hasattr(schema, 'items'):
            self.check_schema(schema.items, results)

        if hasattr(schema, '_request') and schema._request is not None:
            if type(schema._request) not in [Ref, Null]:
                self.check_schema(schema._request, results)

        if hasattr(schema, '_response') and schema._response is not None:
            if type(schema._response) not in [Ref, Null]:
                self.check_schema(schema._response, results)

        if hasattr(schema, 'anyof'):
            for subschema in schema.anyof:
                self.check_schema(subschema, results)

        if hasattr(schema, 'oneof'):
            for subschema in schema.oneof:
                self.check_schema(subschema, results)

        if hasattr(schema, 'allof'):
            for subschema in schema.allof:
                self.check_schema(subschema, results)

        if hasattr(schema, 'not_') and schema.not_ is not None:
            self.check_schema(schema.not_, results)

        if hasattr(schema, '_params'):
            for _, param in schema._params.iteritems():
                self.check_schema(param, results)

        if (isinstance(schema, Merge)):
            self.check_schema(schema.refschema, results)

        if hasattr(schema, 'relations') and len(schema.relations) > 0:
            for relation in schema.relations.items():
                # relation[1] is type of jsonschema.Relation
                self.check_schema(relation[1], results)

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
        results.extend(self._run_rules(Validator.SERVICEDEF_RULES, sdef))

        print('Checking types')
        for typedef in sdef.type_iter():
            if type(typedef) is not Ref:
                results.extend(self._run_rules(Validator.TYPE_RULES +
                                               Validator.SCHEMA_RULES,
                                               typedef))
                self.check_sub_schema(typedef, results)

        print('Checking resources')
        for resource in sdef.resource_iter():
            if type(resource) is not Ref:
                results.extend(self._run_rules(Validator.RESOURCE_RULES +
                                               Validator.SCHEMA_RULES,
                                               resource))
                self.check_sub_schema(resource, results)

            if self.VERBOSITY > 1:
                print('Checking links for \'{}\''.format(resource.name))

            for _, link in resource.links.items():
                if type(link) is not Ref:
                    results.extend(self._run_rules(Validator.LINK_RULES +
                                                   Validator.SCHEMA_RULES,
                                                   link))
                    self.check_sub_schema(link, results)
        return results

    def _run_rules(self, rules, obj):
        """
        Runs a block of rules on a schema object

        :param rules: List of rules to run
        :param obj: reschema object to run the rules on

        :return: List of Result objects
        """

        results = []
        for rule in rules:
            try:
                rule(obj)
                result = Result(rule.rule_id, obj.id, Result.PASSED)

            except ValidationFail as exc:
                result = Result(rule.rule_id, obj.id, Result.FAILED,
                                exc.message)

            except RuleDisabled:
                result = Result(rule.rule_id, obj.id, Result.DISABLED)

            if (result.status != Result.PASSED) or (self.VERBOSITY > 1):
                print(str(result))

            results.append(result)

        return results


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
    for line_number in errors:
        print ("FAIL: [C0007] - line {0} indentation should be 4 spaces"
               .format(line_number))

    return xref_failures + failures + indent_failures


def first_char_pos(line):
    """
    return the indentation of first non-space character of the line
    If the first char is # or none such char exists, return False
    """
    ind = 0
    while ind < len(line):
        if line[ind] == ' ':
            ind += 1
        elif line[ind] == '#':
            return False
        else:
            return ind
    return False


def check_indentation(filename):
    """
    check if each indentation is 4 spaces, otherwise generate issue C0007
    rule: when the first non-whitespace character is '#', ignore.
          otherwise, the indentation of the first valid char is deeper
          than the previous indentation, then the delta must be 4 spaces
    """
    try:
        f = open(filename, 'r')
        # return a list of strings
        list = f.read().split('\n')
        ind = 0
        while ind < len(list) and first_char_pos(list[ind]) is False:
            ind += 1
        pre_pos = first_char_pos(list[ind])
        curr_pos = 0
        errors = []
        while ind < len(list):
            curr_pos = first_char_pos(list[ind])
            ind += 1
            if curr_pos is False:
                continue
            if not (curr_pos == pre_pos or curr_pos == pre_pos + 4 or
                    (pre_pos > curr_pos and (pre_pos - curr_pos) % 4 == 0)):
                errors.append(ind)
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
        raise ValidationFail("'{0}' contains invalid characters"
                             "(only a-z, 0-9, _)".format(location))

    if not re.match('^[a-z]', name):
        raise ValidationFail("'{0}' does not start with a letter"
                             .format(location))


def check_name_length(name, location):
    """
    Check that a name is at least 2 characters long and contain a vowel
    """
    if len(name) < 2:
        raise ValidationFail("'{0}' should be at least 2 characters long"
                             .format(location))


def check_valid_description(text, location, required=True):
    """
    Checks the text of a description
    """
    if not text and required:
        raise ValidationFail("'{0}' has no description field".format(location))

    if not text[0].isupper():
        raise ValidationFail("'{0}' description does not begin with uppercase "
                             "character".format(location))


@Validator.servicedef('W0001')
def schema_provider_valid(sdef):
    if sdef.provider != 'riverbed':
        raise ValidationFail("'provider' field must be 'riverbed'")


@Validator.servicedef('W0002')
def schema_id_valid(sdef):
    id_re = Validator.RVBD_BASE_URL + '/([a-z0-9_.]+)/([0-9](.[0-9]){1,2})$'
    match = re.match(id_re, sdef.id)
    if not match:
        raise ValidationFail("'id' must be '{0}/<name>/<version>'".format(
                             Validator.RVBD_BASE_URL))
    name = match.group(1)
    if name != sdef.name:
        raise ValidationFail("schema id does not match the schema name: '{0}'"
                             .format(sdef.name))
    version = match.group(2)
    if version != sdef.version:
        raise ValidationFail("schema id does not match the schema version: "
                             "'{0}'".format(sdef.version))


@Validator.servicedef('W0003')
def schema_field_valid(sdef):
    schema_re = Validator.RVBD_BASE_URL + '/service_def/([0-9](.[0-9]){1,2})$'
    match = re.match(schema_re, sdef.schema)
    if not match:
        raise ValidationFail("'$schema' field must be"
                             "'{0}/service_def/<version>'"
                             .format(Validator.RVBD_BASE_URL))


@Validator.servicedef('W0004')
def schema_has_title(sdef):
    if not sdef.title:
        raise ValidationFail("the schema must have a title")


@Validator.schema('C0001')
def schema_has_valid_name(schema):
    check_valid_identifier(schema.name, schema.id)


@Validator.typedef('C0002')
def type_does_not_have_prefix_or_suffix(typedef):
    # Some people suffix or prefix the name with type, not needed with the
    # 2.1 $ref: #/types syntax
    type_lc = typedef.name.lower()
    if type_lc.startswith('type'):
        raise ValidationFail("'{0}' should not start with 'type'"
                             .format(typedef.id))
    elif type_lc.endswith('type'):
        raise ValidationFail("'{0}' should not end with 'type'"
                             .format(typedef.id))


@Validator.resource('C0003')
def resource_does_not_have_prefix_or_suffix(resource):
    res_lc = resource.name.lower()
    if res_lc.startswith('resource'):
        raise ValidationFail("'{0}' should not start with 'resource'"
                             .format(resource.id))
    elif res_lc.endswith('resource'):
        raise ValidationFail("'{0}' should not end with 'resource'"
                             .format(resource.id))


@Validator.link('C0004')
def link_does_not_have_prefix_or_suffix(link):
    link_lc = link.name.lower()
    if link_lc.startswith('link'):
        raise ValidationFail("'{0}' should not start with 'link'"
                             .format(link.id))
    elif link_lc.endswith('link'):
        raise ValidationFail("'{0}' should not end with 'link'"
                             .format(link.id))


@Validator.schema('C0005')
def schema_name_check_length(schema):
    check_name_length(schema.name, schema.id)


@Validator.servicedef('C0006')
def sd_has_valid_description(sdef):
    check_valid_description(sdef.description, 'ServiceDef', required=True)


@Validator.link('C0100')
def link_std_has_no_description(link):
    if link.name in Validator.STD_LINKS and link.description:
        raise ValidationFail("'{0}' link must have no description".format(
                             link.name))


@Validator.link('C0101')
def link_non_std_has_description(link):
    if link.name not in Validator.STD_LINKS:
        check_valid_description(link.description, link.id, required=True)


@Validator.link('W0100')
def link_get_has_no_request_body(link):
    if 'get' == link.name and 'null' != link.request.typestr:
        raise ValidationFail("'get' link cannot have a request body")


@Validator.link('W0101')
def link_get_response_is_the_resource(link):
    if 'get' == link.name and link.schema.id != link.response.id:
        raise ValidationFail("'get' link response must be '{0}' ".format(
                             link.schema.id))


@Validator.link('W0102')
def link_set_request_is_the_resource(link):
    if 'set' == link.name and link.schema.id != link.request.id:
        raise ValidationFail("'set' link request must be '{0}' ".format(
                             link.schema.id))


@Validator.link('W0103')
def link_set_response_is_null_or_resource(link):
    if ('set' == link.name and
            'null' != link.response.typestr and
            link.schema.id != link.response.id):
        raise ValidationFail("'set' link response must be empty or '{0}'"
                             .format(link.schema.id))


@Validator.link('W0104')
def link_delete_has_no_request_body(link):
    if 'delete' == link.name and 'null' != link.request.typestr:
        raise ValidationFail("'delete' link cannot have a request body")


@Validator.link('W0105')
def link_delete_has_no_response_body(link):
    if 'delete' == link.name and 'null' != link.response.typestr:
        raise ValidationFail("'delete' link cannot have a response body")


@Validator.link('W0106')
def link_create_has_request_body(link):
    if 'create' == link.name and 'null' == link.request.typestr:
        raise ValidationFail("'create' link must have a request body")


@Validator.link('W0107')
def link_create_request_is_not_resource(link):
    if 'create' == link.name and link.schema.id == link.request.id:
        raise ValidationFail("'create' request must not be '{0}'".format(
                             link.schema.id))


@Validator.link('W0108')
def link_create_response_is_not_resource(link):
    if 'create' == link.name and link.schema.id == link.response.id:
        raise ValidationFail("'create' response must not be '{0}'".format(
                             link.schema.id))


@Validator.link('E0100')
def link_get_method_is_get(link):
    if 'get' == link.name and 'GET' != link.method.upper():
        raise ValidationFail("'get' link must use http method GET")


@Validator.link('E0101')
def link_set_method_is_put(link):
    if 'set' == link.name and 'PUT' != link.method.upper():
        raise ValidationFail("'set' link must use http method PUT")


@Validator.link('E0102')
def link_create_method_is_post(link):
    if 'create' == link.name and 'POST' != link.method.upper():
        raise ValidationFail("'create' link must use http method POST")


@Validator.link('E0103')
def link_delete_method_is_delete(link):
    if 'delete' == link.name and 'DELETE' != link.method.upper():
        raise ValidationFail("'delete' link must use http method DELETE")


@Validator.resource('C0300')
def resource_has_valid_description(resource):
    check_valid_description(resource.description, resource.id, required=True)


@Validator.resource('C0301')
def resource_type_is_object(resource):
    # NOTE: relint does not load referenced files yet.
    if resource.is_ref():
        print("Referenced schema not validated: '{0}'".format(
              resource.refschema.fullid()))
        return
    if 'object' != resource.typestr:
        raise ValidationFail("resource '{0}' should be an object".format(
                             resource.name))


@Validator.typedef('C0200')
def type_has_valid_description(typedef):
    check_valid_description(typedef.description, typedef.id, required=True)


@Validator.schema('E0002')
def required_is_valid(schema):
    if (hasattr(schema, 'required') and hasattr(schema, 'properties')
            and hasattr(schema, 'additional_properties')):
        if (schema.additional_properties is False and
                schema.required is not None):
            for k in schema.required:
                if k not in schema.properties:
                    raise ValidationFail("Required field '{0}' should be "
                                         "included in properties".format(k))


@Validator.schema('E0003')
def relation_is_valid(schema):
    if isinstance(schema, Relation):
        try:
            schema.resource
        except InvalidReference:
            raise ValidationFail("Invalid relation '{0}': '{1}' not found".
                                 format(schema.fullname(),
                                        schema._resource_id))


@Validator.link('E0105')
def link_uritemplate_param_declared(link):
    params = uritemplate.variables(link.path.template)
    for param in params:
        if param not in link.schema.properties:
            raise ValidationFail("The parameter '{0}' in the uritemplate '{1}'"
                                 " is not declared in properties in '{2}'".
                                 format(param, link.path.template,
                                        link.schema.fullname()))
