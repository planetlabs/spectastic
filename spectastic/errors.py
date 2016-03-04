# -*- coding: utf-8 -*-


class ValidationErrors(Exception):
    def __init__(self, errors=None):
        if errors is None:
            errors = []

        self.errors = errors

    def __repr__(self):
        return 'ValidatorError([{}])'.format(
            ', '.join([repr(error) for error in self.errors])
        )


class FieldError(Exception):
    VALID_LOCATIONS = ['header', 'body', 'query', 'path']

    def __init__(self, msg, location, field):
        """
        :param msg: The associated exception message.
        :param location: The location of the field e.g header, body, query.
        :param field: The name of the field.
        """
        if location not in self.VALID_LOCATIONS:
            raise ValueError('Field location invalid, should be in: {}'.format(
                ', '.join(self.VALID_LOCATIONS)
            ))
        self.msg = msg
        self.location = location
        self.field = field

    def __repr__(self):
        return "FieldError('{}', '{}', '{}')".format(
            self.msg,
            self.location,
            self.field,
        )
