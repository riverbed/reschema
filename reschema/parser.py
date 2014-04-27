from reschema.exceptions import ParseError
from reschema.util import check_type


class Parser(object):
    """ Input object parser. """
    def __init__(self, input, obj, name):
        if not isinstance(input, dict):
            raise ParseError('%s: definition should be a dictionary, got: %s' %
                             (name, type(input)), input)
        self.input = input
        self.obj = obj
        self.name = name
        self.parsed_props = set()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if type is None:
            # parsing was all successful, check that all input keys
            # were parsed
            self.check_input()
            return True

    def parse(self, prop, default_value=None, required=False,
              types=None, save=True):
        """Parse a key from the input dict.

        :param string prop: Property name to extract

        :param default_value: A value to use if the property is missing
            but not required.  Ignored if `required` is True.

        :param bool required: Causes ParseError to be raised if `prop`
            is not in the input

        :param list types: verifies that the property value is an
            instance of at least one of the types passed in this
            parameter.

        :param save: If true, save the property to this parsers
            object, if false, don't save.  Otherwise use save value as
            the property name to save as

        :raises reschema.exceptions.ParseError: if the type of the
            data is incorrect or if the property is required but
            missing.

        :return: The parsed value.
        """

        if prop in self.input:
            val = self.input[prop]
            if types:
                check_type(prop, val, types, self.input)
            self.parsed_props.add(prop)

        elif required:
            raise ParseError(
                "Missing required property '%s'" % prop, self.input)
        else:
            val = default_value

        if save is not False and self.obj is not None:
            if save is True:
                setattr(self.obj, prop, val)
            else:
                setattr(self.obj, save, val)

        return val

    def check_input(self):
        """ Verify that all input properities were parsed. """
        if input is None:
            return

        unparsed = set(self.input.keys()).difference(self.parsed_props)

        if len(unparsed) > 0:
            raise ParseError(
                '%s: unrecognized properties in definition: %s' %
                (self.name, ','.join(unparsed)), list(unparsed)[0])
