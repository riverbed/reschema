# Copyright (c) 2014 Riverbed Technology, Inc.

from __future__ import print_function

import sys
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
                print('FAIL: [{0}] - {1}'.format(rule.rule_id, exc.message))

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


def check_name_length_and_vowels(name, location):
    """
    Check that a name is at least 3 characters long and contain a vowel
    """
    if len(name) < 3:
        raise ValidationFail("'{0}' should be at least 3 characters long"
                             .format(location))

    try:
        re.search('[aeiou]', name, re.I).start()
    except AttributeError:
        raise ValidationFail("'{0}' contains no vowels".format(location))


def check_valid_description(text, location, required=True):
    """
    Checks the text of a description
    """
    if not text and required:
        raise ValidationFail("'{0}' has no description field".format(location))

    if not text[0].isupper():
        raise ValidationFail("'{0}' description does not begin with uppercase"
                             "character".format(location))


@Validator.servicedef('W0001')
def schema_provider_valid(sdef):
    if sdef.provider != 'riverbed':
        raise ValidationFail("'provider' field must be 'riverbed'")


@Validator.servicedef('W0003')
def schema_field_valid(sdef):
    schema_val = 'http://support.riverbed.com/apis/service_def/2.1'

    if sdef.schema != schema_val:
        raise ValidationFail(
            "'$schema' field should be set to '{0}'".format(schema_val))


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
def type_does_not_have_suffix(typedef):
    # Some people suffix the name with _type, not needed with the
    # 2.1 $ref: #/types syntax
    if typedef.name.endswith('_type'):
        raise ValidationFail("'{0}' should not be suffixed with '_type'"
                             .format(typedef.id))


@Validator.resource('C0003')
def resource_does_not_have_suffix(resource):
    if resource.name.endswith('_resource'):
        raise ValidationFail("'{0}' should not be suffixed with '_resource'"
                             .format(resource.id))


@Validator.link('C0004')
def link_does_not_have_suffix(link):
    if link.name.endswith('_link'):
        raise ValidationFail("'{0}' should not be suffixed with '_link'"
                             .format(link.id))


@Validator.typedef('C0005')
def type_name_check_length_and_vowels(typedef):
    check_name_length_and_vowels(typedef.name, typedef.id)


@Validator.resource('C0005')
def resource_name_check_length_and_vowels(resource):
    check_name_length_and_vowels(resource.name, resource.id)


@Validator.link('C0005')
def link_name_check_length_and_vowels(link):
    check_name_length_and_vowels(link.name, link.id)


@Validator.servicedef('C0007')
def schema_has_valid_description(sdef):
    check_valid_description(sdef.description, 'ServiceDef', required=True)


@Validator.resource('C0300')
def resource_has_valid_description(resource):
    check_valid_description(resource.description, resource.id)
