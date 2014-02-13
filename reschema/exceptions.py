# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


#
# General exception and base class
#
class ReschemaException(Exception):
    """ Base exception class for reschema errors. """


class UnsupportedSchema(ReschemaException):
    """ Schema uses an unsupported schema format. """
    pass


class NoContext(ReschemaException):
    """ A relative reference was provided with no supporting context. """

    def __init__(self, reference):
        self._reference = reference

    def __str__(self):
        return ("Relative reference connot be resolve without context: %s"
                % self._reference)


#
# jsonschema parsing errors
#
class MarkedError(ReschemaException):
    """ Base exception class for marked schema objects. """
    def __init__(self, message, obj):
        super(MarkedError, self).__init__(message)
        self.obj = obj
        try:
            self.start_mark = obj.start_mark
            self.end_mark = obj.end_mark
        except AttributeError:
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

