# -*- coding: utf-8 -*-
from copy import deepcopy
from urllib2 import unquote
from itertools import chain
import jsonschema
import re

import logging
logger = logging.getLogger(__name__)

from werkzeug.datastructures import MultiDict, Headers
from .errors import ValidationErrors, FieldError
from .validators import SwaggerValidator


# These locations are *not* intended for body params which should already
# be the correct type. All other param locations are strings.
STRINGLY_LOCATIONS = ['path', 'query', 'headers']
VALID_LOCATIONS = STRINGLY_LOCATIONS + ['body']


class OperationNotFound(Exception):
    """
    Raised when an operation cannot be found in a schema.
    """


class InvalidPath(Exception):
    """
    Raised when a path does not match an operation's route.
    """


def find_operation(schema, operation_id):
    """
    Returns a tuple of the route, method and schema for an operation.

    :raises: :class:`OperationNotFound`
        When the operation_id does not exist anywhere in the sec.
    """
    # TODO a reverse index would be quicker but would require guarantees
    # that the schema dictionary is immutable.
    for route, schema in schema['paths'].iteritems():
        for method, subschema in schema.iteritems():
            if subschema.get('operationId') == operation_id:
                return (route, method, subschema)
    raise OperationNotFound('Could not find {}'.format(operation_id))

def coerce_param(value, schema):
    """
    Coerces a named parameter within a path, query, or headers to the
    type specified in the appropriate schema. If the string is not
    properly formated, raise a FieldError.

    :param string value:
        The stringified value
    :param dict schema:
        The schema dictionary for the parameter.
    :raises: :class:`~spectastic.errors.FieldError`
        When the primitive type is not coercible.
    :return:
        The value, coerced according to the parameter definition for the
        field named ``name`` located in ``location``.
    """

    location = schema['in']
    name = schema['name']

    if location not in STRINGLY_LOCATIONS:
        raise ValueError('Field location invalid, should be in: {}'.format(
            ', '.join(STRINGLY_LOCATIONS)
        ))

    # Open API defines 3 primitive types. They're simple enough to handle
    # within these conditionals without resorting to specialized methods.
    if schema['type'] == 'integer':
        if not re.match('^\-?[0-9]|[1-9][0-9]*$', value):
            raise FieldError(
                'Field {} is not an integer'.format(name),
                location,
                name,
            )
        try:
            return int(value)
        except ValueError:
            raise FieldError(
                'Field {} is not an integer'.format(name),
                location,
                name,
            )
    elif schema['type'] == 'number':
        try:
            return float(value)
        except ValueError:
            raise FieldError(
                'Field {} is not a number'.format(name),
                location,
                name
            )
    elif schema['type'] == 'boolean':
        if value not in  ['true', 'false']:
            raise FieldError(
                # flake8: noqa
                'Field {} is not a boolean, expected `true` or `false` got `{}'.format(name, value),
                location,
                name
            )
        elif value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            raise RuntimeError('Botched boolean cooercion')
    elif schema['type'] == 'string':
        return value
    else:
        raise ValueError('Unknown type specified in schema {}'.format(
            schema['type']
        ))


class Operation(object):

    @staticmethod
    def from_schema(schema, operation_id):
        route, method, local_schema = find_operation(schema, operation_id)
        return Operation(schema, route, method, local_schema)

    def __init__(self, schema, route, method, local_schema):
        """
        :param dict schema: The overall schema for this API.
        :param dict local_schema: The schema specific to this operation.
        :param string route: The route for this operation.
        :param string method: The http method for this operation.
        """
        self.schema = schema
        self.local_schema = local_schema
        self.route = route
        self.method = method.upper()

    # Convenience methods for accessing parameter types for this operation.
    # ---------------------------------------------------------------------

    def _param_schemas(self, location):
        if location not in ['query', 'body', 'path', 'header']:
            raise ValueError('Unknown parameter location: {}'.format(location))

        return {
            schema['name'].lower(): schema for schema in
            self.local_schema['parameters']
            if schema['in'] == location
        }

    def header_schemas(self):
        """
        Returns a list of all header parameter schemas.
        """
        return self._param_schemas('header')

    def query_schemas(self):
        """
        Returns a list of all query parameter schemas.
        """
        return self._param_schemas('query')

    def path_schemas(self):
        """
        Returns a list of all path parameter schemas.
        """
        return self._param_schemas('path')

    def body_schema(self):
        """
        Returns a tuple of consisting of the body parameter and it's corresponding
        body schema.
        """
        for schema in self.local_schema['parameters']:
            if schema['in'] == 'body':
                return schema, schema['schema']
        else:
            return None, {}

    # Param munging. Because non-body input params arrive as strings.
    # Singular, case insensitive-accessors for schemas on a named parameter.
    # ----------------------------------------------------------------------

    def path_schema(self, path_param_name):
        """
        Returns the schema for a path parameter of a given name. The parameter
        name is case-insensitive.

        :raises: :class:`KeyError`
            If the query is not found.
        """
        path_schemas = self.path_schemas()
        return path_schemas[path_param_name.lower()]

    def query_schema(self, query_param_name):
        """
        Returns the schema for a query parameter of a given name. The parameter
        name is case-insensitive.

        :raises: :class:`KeyError`
            If the query is not found.
        """
        query_schemas = self.query_schemas()
        return query_schemas[query_param_name.lower()]

    def header_schema(self, header_name):
        """
        Returns the schema for a header parameter of a given name. The parameter
        name is case-insensitive.

        :raises: :class:`KeyError`
            If the header is not found.
        """
        header_schemas = self.header_schemas()
        return header_schemas[header_name.lower()]

    @property
    def validator(self):
        if not hasattr(self, '_validator'):
            self._validator = SwaggerValidator(
                self.schema, format_checker=jsonschema.draft4_format_checker,
            )
        return self._validator

    @property
    def _path_matcher(self):
        """
        Returns a memoized, compiled regular expression matcher built for
        this operations route.
        """
        if not hasattr(self, '__path_matcher'):
            path_schemas = self.path_schemas()
            path_subs = {
                path_schema['name']: '(?P<{}>[^/]*)'.format(
                    path_schema['name']
                ) for path_schema in path_schemas.values()
            }

            # Swagger routes are conveniently easy to substitute.
            path_expr = '^{}/{}$'.format(
                self.schema.get('basePath','').rstrip('/'),
                self.route.lstrip('/').format(**path_subs)
            )

            # If there's still braces left in the route we've missed a parameter.
            # in the schema and it's invalid.
            if '{' in path_expr or '}' in path_expr:
                # flake8: noqa
                raise RuntimeError('Unmatched parameters remain after route substitution: {}'.format(path_expr))

            self.__path_matcher = re.compile(path_expr)

        return self.__path_matcher

    def extract_path_args(self, path):
        """
        Matches a request path against this operation's route, returning an
        intermediate dictionary of strings for each path parameter. The
        resulting dictionary is not validated nor are it's types coerced.

        :return dict:
            A dictionary of path arguments, with keys corresponding to the case
            sensitive name specified in the swagger schema.
        """
        match = self._path_matcher.match(path)
        if match:
            return {
                key: unquote(value).decode('utf8')
                for key, value in match.groupdict().iteritems()
            }
        else:
            raise InvalidPath()

    # Iterative validation methods for each parameter location.
    # ---------------------------------------------------------

    def iter_request_body_errors(self, request_body):
        """
        Validates a request body against the schema, yielding
        a :class:`~spectastic.errors.FieldError` for each failure.
        """
        body_param, body_schema = self.body_schema()
        if body_param:
            if body_param.get('required') == True \
                    and not hasattr(request_body, 'iteritems'):
                yield FieldError(
                    "A request body is required and must be an object",
                    'body',
                    body_param['name']
                )
                return

            for error in self.validator.iter_errors(request_body, body_schema):
                # Relies on our overriden 'required' validator to provide
                # an error path.
                path = error.path
                yield FieldError(error.message, 'body', '.'.join(map(
                    str, path
                )))


    def iter_request_path_errors(self, request_path):
        """
        Validates a request path against the schema, yielding
        a :class:`~spectastic.errors.FieldError` for each failure.
        """
        path_schemas = self.path_schemas()
        if len(path_schemas) == 0:
            return

        params = self.extract_path_args(request_path)
        for param, value in params.iteritems():
            param = param.lower()
            # The input is a string that we need to type case at least partially
            # before passing to jsonschema, which expects the primitive type
            # to be correct (as it's intended for use with json data).
            if param in path_schemas:
                schema = self.path_schema(param)

                try:
                    value = coerce_param(value, schema)
                except FieldError:
                    yield FieldError(
                        'Invalid type for {}'.format(schema['name']),
                        'path',
                        schema['name'],
                    )

                for error in self.validator.iter_errors(value, schema):
                    yield FieldError(
                        error.message, 'path', schema['name']
                    )
        for name, schema in path_schemas.iteritems():
            if schema.get('required') == True and schema['name'] not in params:
                yield FieldError(
                    'Required path parameter is missing',
                    'path',
                    schema.get('name')
                )

    def iter_request_header_errors(self, request_headers):
        """
        Validates individual request headers against the schema, yielding
        a :class:`~spectastic.errors.FieldError` for each failure.
        """
        header_schemas = self.header_schemas()
        if len(header_schemas) == 0:
            return

        request_headers = Headers(request_headers)

        for header, value in request_headers.iteritems():
            if header in header_schemas:
                schema = self.header_schema(header)
                for error in self.validator.iter_errors(value, schema):
                    yield FieldError(error.message, 'header', header)

        for name, schema in header_schemas.iteritems():
            if schema.get('required') and name.lower() \
                    not in request_headers:
                yield FieldError(
                    'Required header is missing',
                    'header',
                    schema.get('name')
                )

    def iter_request_query_errors(self, query_params):
        """
        Validates a request query against the schema, yielding
        a :class:`~spectastic.errors.FieldError` for each failure.
        """
        query_schemas = self.query_schemas()
        if len(query_schemas) == 0:
            return
        # For MultiDicts, which are preferred because http requests support
        # multiple query parameters of the same name, we pass the multi
        # argument to ensure we iterate over every query parameter.
        if isinstance(query_params, MultiDict):
            iterargs = {'multi': True}
        else:
            iterargs = {}

        for name, value in query_params.iteritems(**iterargs):
            if name in query_schemas:
                schema = deepcopy(self.query_schema(name))
                # The required validator won't work in the context of a single
                # value. We remove it validate it in a subsequent loop.
                if 'required' in schema:
                    schema.pop('required')

                try:
                    value = coerce_param(value, schema)
                except FieldError:
                    yield FieldError(
                        'Invalid type for {}'.format(schema['name']),
                        'path',
                        schema['name'],
                    )

                for error in self.validator.iter_errors(value, schema):
                    yield FieldError(
                        error.message,
                        'query',
                        schema['name']
                    )

        for name, schema in query_schemas.iteritems():
            if schema.get('required', False) and name not in query_params:
                yield FieldError(
                    'Required query parameter is missing',
                    'query',
                    schema.get('name')
                )

    def iter_request_errors(self, request):
        """
        Validates an entire request, yielding a
        :class:`~spectastic.errors.FieldError` for each failure.

        :param ~spectastic.request.BasicRequest request:
            A request conforming to the structure outlined in
            :class:`~spectastic.request.BasicRequest`
        """
        for error in chain(
            self.iter_request_body_errors(request.body),
            self.iter_request_path_errors(request.path),
            self.iter_request_query_errors(request.query),
            self.iter_request_header_errors(request.headers),
        ):
            yield error

    # ValidationError raising methods for each parameter location
    # -----------------------------------------------------------

    def validate_request_body(self, request_body):
        """
        Validates a request body against the operation schema.

        :raises: :class:`~spectastic.errors.ValidationErrors`
            When validation fails.
        :return bool: True on success.
        """
        errors = list(self.iter_request_body_errors(request_body))
        if errors:
            raise ValidationErrors(errors)
        else:
            return True

    def validate_request_path(self, path_arguments):
        """
        Validates headers against the operation.

        :raises: :class:`~spectastic.errors.ValidationErrors`
            When validation fails.
        :return bool: True on success.
        """
        errors = list(self.iter_request_path_errors(path_arguments))
        if errors:
            raise ValidationErrors(errors)
        else:
            return True

    def validate_request_headers(self, headers):
        """
        Validates headers against the operation.

        :raises: :class:`~spectastic.errors.ValidationErrors`
            When validation fails.
        :return bool: True on success.
        """
        errors = list(self.iter_request_header_errors(headers))
        if errors:
            raise ValidationErrors(errors)
        else:
            return True

    def validate_request_query(self, query_params):
        """
        Validates the query parameters from a request.

        :param dict|werkzeug.datastructures.MultiDict query_params:
            A dictionary like object of query parameters.
        :raises: :class:`~spectastic.errors.ValidationErrors`
            When validation fails.
        :return bool: True on success.
        """
        errors = list(self.iter_request_query_errors(query_params))
        if errors:
            raise ValidationErrors(errors)
        else:
            return True

    def validate_request(self, request):
        """
        Validates all components of a request.

        :param request:
            A request conforming to the structure outlined in
            :class:`~spectastic.request.BasicRequest`
        :raises: :class:`~spectastic.errors.ValidationErrors`
            When validation fails.
        :return bool: True on success.
        """
        errors = list(self.iter_request_errors(request))
        if errors:
            raise ValidationErrors(errors)
        else:
            return True
