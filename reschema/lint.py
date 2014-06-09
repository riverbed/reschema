# Copyright (c) 2014 Riverbed Technology, Inc.

from __future__ import print_function

import re


class ValidationFail(Exception):
    """
    Schema did something it shouldn't have
    """
    pass


class Rule(object):
    def __init__(self, rule_id, rule_func):
        self.rule_id = rule_id
        self.rule_func = rule_func


class Validator(object):
    SCHEMA_RULES = []
    TYPE_RULES = []
    RESOURCE_RULES = []
    LINK_RULES = []
    VERBOSITY = 0
    RVBD_BASE_URL = 'http://support.riverbed.com/apis'
    STD_LINKS = ['self', 'get', 'set', 'delete', 'create']

    @classmethod
    def servicedef(cls, rule_id):
        def wrapper(rule_func):
            cls.SCHEMA_RULES.append(Rule(rule_id, rule_func))
            return rule_func
        return wrapper

    @classmethod
    def typedef(cls, rule_id):
        def wrapper(rule_func):
            cls.TYPE_RULES.append(Rule(rule_id, rule_func))
            return rule_func
        return wrapper

    @classmethod
    def resource(cls, rule_id):
        def wrapper(rule_func):
            cls.RESOURCE_RULES.append(Rule(rule_id, rule_func))
            return rule_func
        return wrapper

    @classmethod
    def link(cls, rule_id):
        def wrapper(rule_func):
            cls.LINK_RULES.append(Rule(rule_id, rule_func))
            return rule_func
        return wrapper

    @classmethod
    def set_verbosity(cls, level):
        cls.VERBOSITY = level

    @classmethod
    def run_rules(cls, rules, obj):
        failures = 0
        for rule in rules:
            try:
                rule.rule_func(obj)
                if cls.VERBOSITY > 1:
                    print('PASS: [{0}] - \'{1}\''.format(rule.rule_id, obj.id))

            except ValidationFail as exc:
                failures += 1
                print('FAIL: [{0}] - <{1}> - {2}'.format(
                      rule.rule_id, obj.id, exc.message))

        return failures


def lint(sdef):
    """
    Performs all checks on a loaded service definition.
    """

    failures = 0
    print('Checking top-level schema correctness')
    failures += Validator.run_rules(Validator.SCHEMA_RULES, sdef)

    print('Checking types')
    for typedef in sdef.type_iter():
        failures += Validator.run_rules(Validator.TYPE_RULES, typedef)

    print('Checking resources')
    for resource in sdef.resource_iter():
        failures += Validator.run_rules(Validator.RESOURCE_RULES, resource)
        print('Checking links for resource \'{}\''.format(resource.name))
        for _, link in resource.links.items():
            failures += Validator.run_rules(Validator.LINK_RULES, link)

    # TODO: load cross-referenced schemas
    print('Checking referenced types and resources')
    errors = sdef.check_references()
    if errors:
        for error in errors:
            print('FAIL: [E0001] - \'{0}\' cannot be resolved'
                  .format(error.id))
        failures += len(errors)

    return failures


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


@Validator.typedef('C0001')
def type_has_valid_name(typedef):
    check_valid_identifier(typedef.name, typedef.id)


@Validator.resource('C0001')
def resource_has_valid_name(resource):
    check_valid_identifier(resource.name, resource.id)


@Validator.link('C0001')
def link_has_valid_name(link):
    check_valid_identifier(link.name, link.id)


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


@Validator.typedef('C0005')
def type_name_check_length(typedef):
    check_name_length(typedef.name, typedef.id)


@Validator.resource('C0005')
def resource_name_check_length(resource):
    check_name_length(resource.name, resource.id)


@Validator.link('C0005')
def link_name_check_length(link):
    check_name_length(link.name, link.id)


@Validator.servicedef('C0006')
def schema_has_valid_description(sdef):
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
    if resource.isRef():
        print("Referenced schema not validated: '{0}'".format(
              resource.refschema.fullid()))
        return
    if 'object' != resource.typestr:
        raise ValidationFail("resource '{0}' should be an object".format(
                             resource.name))


@Validator.typedef('C0200')
def type_has_valid_description(typedef):
    check_valid_description(typedef.description, typedef.id, required=True)
