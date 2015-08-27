# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from reschema.loader_nodes import obj_key_node


#
# General exception and base class
#
class ReschemaException(Exception):
    """ Base exception class for reschema errors. """


class UnsupportedSchema(ReschemaException):
    """ Schema uses an unsupported schema format. """
    pass


class InvalidServiceId(ReschemaException):
    """ No service defintion loaded for the given id. """
    pass


class InvalidServiceName(ReschemaException):
    """ No service defintion loaded for the given name. """
    pass


class DuplicateServiceId(ReschemaException):
    """ Service defintion already registered for the requested id. """

    def __init__(self, id_):
        self.id_ = id_

    def __str__(self):
        return "Service definition already registered by id: %s" % self.id_


class NoContext(ReschemaException):
    """ A relative reference was provided with no supporting context. """

    def __init__(self, reference):
        self.reference = reference

    def __str__(self):
        return ("Relative reference cannot be resolved without context: %s"
                % self.reference)


class NoManager(ReschemaException):
    """ A partial/full reference was provided but no ServiceDefManager available. """

    def __init__(self, reference):
        self.reference = reference

    def __str__(self):
        return ("Reference cannot be resolved without a manager: %s"
                % self.reference)


class InvalidReference(ReschemaException):
    """ Invalid reference. """

    def __init__(self, msg, reference):
        self.msg = msg
        self.reference = reference

    def __str__(self):
        return ("Invalid reference '%s': %s" % (self.reference, self.msg))


#
# jsonschema parsing errors
#
class MarkedError(ReschemaException):
    """ Base exception class for marked schema objects. """
    def __init__(self, message, obj=None, parent_obj=None):
        super(MarkedError, self).__init__(message)

        if hasattr(obj, 'start_mark'):
            self.obj = obj
            self.start_mark = obj.start_mark
            self.end_mark = obj.end_mark
        elif (  parent_obj and (obj in parent_obj) and
                hasattr(parent_obj, 'start_mark')):
            self.obj = obj_key_node(parent_obj, obj)
            self.start_mark = self.obj.start_mark
            self.end_mark = self.obj.end_mark
        else:
            self.start_mark = None
            self.end_mark = None

    def __str__(self):
        msg = []
        msg.append(super(MarkedError, self).__str__())
        if self.start_mark:
            msg.append('Source data locations:')
            msg.append('Start mark: ' + str(self.start_mark))
        if self.end_mark:
            msg.append('End mark:   ' + str(self.end_mark))
        return '\n'.join(msg)


class MissingParameter(MarkedError):
    """ Missing link parameters. """


class ParseError(MarkedError):
    """ Schema parsing error. """


#
# jsonschema validation errors
#
class ValidationError(ReschemaException):
    """ Schema validation error. """


class ReschemaLoadHookException(Exception):
    """ Exceptions as a result of attempting loading via hooks. """
