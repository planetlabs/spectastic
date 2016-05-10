#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_spectastic
----------------------------------

Tests for `spectastic` module.
"""
from math import isnan
from mock import patch
import json

from hypothesis import (
    strategies as st,
    assume,
    given,
)
from werkzeug.datastructures import MultiDict, Headers
import unittest

from spectastic.operation import (
    Operation,
    OperationNotFound,
    coerce_param,
)
from spectastic.schema import (
    Schema,
)
from spectastic.errors import (
    ValidationErrors,
)
from spectastic.request import (
    BasicRequest,
)
from .spec import (
    generate_schema,
    generate_method,
    generate_param,
)


from .spec import SPEC


class TestSchema(unittest.TestCase):

    def test_spec_copy(self):
        original_dict = {'definitions': 'Woot'}
        spec = Schema(original_dict)
        spec['definitions'] = 'Bar'
        self.assertEqual(
            'Bar',
            spec['definitions']
        )
        self.assertEqual(
            'Woot',
            original_dict['definitions']
        )

    def test_spec_resolution(self):
        spec = Schema(SPEC)
        self.assertEqual(
            spec['definitions']['Error'],
            spec['definitions']['NastyError']['allOf'][0]
        )

    def test_spec_resolution_depth(self):
        spec = Schema(SPEC)

        def _validate_current(current, path=None):
            if path is None:
                path = ['spec']

            if isinstance(current, dict):
                for key, value in current.iteritems():
                    if key == '$ref':
                        self.fail('Found a ref at {}:{}'.format(
                            path + key, value
                        ))
                    _validate_current(value, path + [key])
            if isinstance(current, list):
                for key, value in enumerate(current):
                    _validate_current(value, path)

        _validate_current(spec)


class TestCoercion(unittest.TestCase):

    @given(st.integers())
    def test_coercion_int(self, hypo):
        value = unicode(hypo)
        schema = {
            'name': 'param',
            'in': 'path',
            'type': 'integer',
            'format': 'int32',
            'name': 'Thing',
        }
        self.assertEqual(hypo, coerce_param(value, schema))

    @given(st.floats())
    def test_coercion_float(self, hypo):
        assume(not isnan(hypo))
        value = "{:.9f}".format(hypo)
        schema = {
            'name': 'param',
            'in': 'path',
            'type': 'number',
            'format': 'double',
            'name': 'Thing',
        }
        self.assertAlmostEqual(hypo, coerce_param(value, schema), 5)

    @given(st.text())
    def test_coercion_text(self, hypo):
        value = unicode(hypo)
        schema = {
            'name': 'param',
            'in': 'path',
            'type': 'string',
            'name': 'Thing',
        }
        self.assertEqual(hypo, coerce_param(value, schema))


class TestBasicRequest(unittest.TestCase):

    def test_request_body_json(self):
        request = BasicRequest(
            '{"hello": "world"}', {'content-type': 'application/json'}, '', '')
        self.assertEqual(
            request.body,
            {"hello": "world"}
        )

    def test_request_body_dict(self):
        request = BasicRequest(
            {"hello": "world"}, {'content-type': 'application/json'}, '', '')
        self.assertEqual(
            {"hello": "world"},
            request.body,
        )

    def test_request_body_null(self):
        request = BasicRequest(
            'null', {'content-type': 'application/json'}, '', '')
        self.assertEqual(
            None,
            request.body,
        )

    def test_request_body_empty(self):
        request = BasicRequest(
            '', {'content-type': 'application/json'}, '', '')
        self.assertEqual(
            None,
            request.body,
        )

    def test_request_body_raw(self):
        request = BasicRequest(
            'hello', {}, '', '')
        self.assertEqual(
            'hello',
            request.body,
        )

    def test_request_body_headers(self):
        request = BasicRequest(
            None, {'AuthOrization': 'woot'}, '', '')
        self.assertIn(
            'Authorization',
            request.headers,
        )
        self.assertNotIn(
            'derpy',
            request.headers,
        )


class TestOperation(unittest.TestCase):

    def test_from_schema_found(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(
            'GetItem',
            operation.local_schema['operationId'],
        )

    def test_from_schema_missing(self):
        with self.assertRaises(OperationNotFound):
            Operation.from_schema(Schema(SPEC), 'Derp')

    def test_headers_schemas(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        header_schemas = operation.header_schemas()
        self.assertEqual(1, len(header_schemas))
        self.assertEqual(
            'Authorization',
            header_schemas['authorization']['name']
        )

    def test_path_schemas(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        path_schemas = operation.path_schemas()
        self.assertEqual(1, len(path_schemas))
        self.assertEqual('ItemID', path_schemas['itemid']['name'])

    def test_query_schemas(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(1, len(operation.header_schemas()))

    def test_body_schema(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(1, len(operation.header_schemas()))

    def test_path_matcher(self):
        cases = [
            {'base': '/', 'method': '/', 'expected': '/'},
            {'base': '/', 'method': '/woot', 'expected': '/woot'},
            {'base': '/', 'method': '/woot/', 'expected': '/woot/'},
            {'base': '/hello', 'method': 'woot', 'expected': '/hello/woot'},
            {'base': '/hello', 'method': '/woot', 'expected': '/hello/woot'},
            {'base': '/hello', 'method': '/woot/', 'expected': '/hello/woot/'},
        ]
        for case in cases:
            method = generate_method(path=case['method'])
            schema = Schema(generate_schema(
                base_path=case['base'],
                methods=method,
            ))
            operation = Operation.from_schema(schema, 'Get')
            self.assertIsNotNone(
                operation._path_matcher.match(
                    case['expected']
                )
            )


class RequestValidationTests(unittest.TestCase):

    def test_query_parameters_success(self):
        """
        Validates that an operation's query parameters pass validation when
        conforming to an operation's query param specification.
        """
        query = MultiDict([
            ('search', 'woot')
        ])
        operation = Operation.from_schema(Schema(SPEC), 'Search')
        self.assertEqual(True, operation.validate_request_query(query))

    def test_query_parameter_missing(self):
        """
        Validates that an operation's query parameters fail validation when
        not conforming to an operation's query param specification.
        """
        query = {}
        operation = Operation.from_schema(Schema(SPEC), 'Search')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_query(query)
            self.assertEqual('search', exc_info.exception.errors[0].field)

    def test_query_parameter_validation_error(self):
        query = MultiDict([
            ('search', 5)
        ])
        operation = Operation.from_schema(Schema(SPEC), 'Search')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_query(query)
        self.assertEqual('search', exc_info.exception.errors[0].field)

    def test_query_parameter_multidict_validation(self):
        query = MultiDict([
            ('search', 'boop'),
            ('search', 5),
        ])
        operation = Operation.from_schema(Schema(SPEC), 'Search')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_query(query)
        self.assertEqual('search', exc_info.exception.errors[0].field)

    def test_allow_unknown_query_parameter(self):
        """
        Allow unrecognized query parameters.
        """
        query = {'search': 'woot', 'unKnown_param': 'foo'}
        operation = Operation.from_schema(Schema(SPEC), 'Search')
        self.assertEqual(True, operation.validate_request_query(query))

    def test_query_param_types(self):
        """
        Ensures that we validates types of query parameters.
        """
        cases = [
            {'type': 'string', 'value': 'dfs', 'success': True},
            {'type': 'integer', 'value': '5', 'success': True},
            {'type': 'integer', 'value': '-5', 'success': True},
            {'type': 'number', 'value': '5', 'success': True},
            {'type': 'boolean', 'value': 'true', 'success': True},

            {'type': 'integer', 'value': 'x', 'success': False},
            {'type': 'number', 'value': 'x', 'success': False},
            {'type': 'boolean', 'value': 'xxx', 'success': False},
            {'type': 'string', 'format': 'date-time', 'value': 'xxx',
             'success': False},
            {'type': 'string', 'format': 'date-time',
             'value': '2015-05-05T00:00:00.123456Z', 'success': True},
            {'type': 'string', 'format': 'date-time',
             'value': '2015-05-05T00:00:00.123456+00:00', 'success': True},
        ]
        for case in cases:
            param = generate_param(
                'param', 'query', case['type'],
                _format=case.get('format')
            )
            method = generate_method(parameters=[param])
            schema = generate_schema(methods=method)
            operation = Operation.from_schema(Schema(schema), 'Get')
            if case['success']:
                self.assertEqual(
                    True,
                    operation.validate_request_query({'param': case['value']})
                )
            else:
                with self.assertRaises(ValidationErrors):
                    operation.validate_request_query({'param': case['value']})

    def test_header_success(self):
        """
        Validates that an operation's response headers pass validation when
        conforming to an operation's header param specification.
        """
        headers = Headers([
            ('Authorization', 'bearer woot'),
        ])
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(True, operation.validate_request_headers(headers))

    def test_header_success_with_dict(self):
        """
        Validates that we can also validates headers derived from a dict.
        """
        headers = {
            'Authorization': 'bearer woot'
        }
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(True, operation.validate_request_headers(headers))

    def test_header_insensitive_success(self):
        """
        Validates that an operation's response headers pass validation when
        conforming to an operation's header param specification.
        """
        headers = Headers([
            ('authorization', 'bearer woot'),
        ])
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        self.assertEqual(True, operation.validate_request_headers(headers))

    def test_header_error(self):
        """
        Validates that an operation's response headers fail validation when
        not conforming to an operation's header param specification.
        """
        headers = Headers()
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_headers(headers)
        self.assertEqual('Authorization', exc_info.exception.errors[0].field)

    def test_body_success(self):
        """
        Validates that an operation's response body passes validation when
        conforming to an operation's body specification.
        """
        body = {
            'type': 'CandyItem',
            'color': 'red',
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        self.assertEqual(True, operation.validate_request_body(body))

    def test_body_error_unknown_discriminator(self):
        """
        Validates that an operation's response body fails validation when
        the type identified by the discriminator is undefined. In this case,
        'DerpItem' does not appear in the test spec's definitions.
        """
        body = {
            'type': 'DerpItem'
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('type', exc_info.exception.errors[0].field)

    def test_body_error_missing_discriminator(self):
        """
        Validates that an operation's response body fails validation when
        the type identified by the discriminator is undefined. In this case,
        'DerpItem' does not appear in the test spec's definitions.
        """
        body = {}
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('type', exc_info.exception.errors[0].field)

    def test_body_failures_non_object(self):
        """
        Validates an empty request body.
        """
        cases = [None, 5, []]
        for body in cases:
            operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
            with self.assertRaises(ValidationErrors) as exc_info:
                operation.validate_request_body(body)
            self.assertEqual('item', exc_info.exception.errors[0].field)

    def test_body_failures_object(self):
        """
        Validates an empty request body.
        """
        body = {}
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('type', exc_info.exception.errors[0].field)

    def test_body_error_bad_polymorphic_type(self):
        """
        Validates that we also apply the validations for the type referred
        to by the discriminator to the current instance. The fixture is missing
        a required field, `color`.
        """
        body = {
            'type': 'CandyItem'
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('color', exc_info.exception.errors[0].field)

    def test_schemaless_param_success(self):
        """
        Validates that we allow arbitrary bodies when a body parameter
        hasn't been specified.
        """
        body = {'type': 'CandyItem'}
        query = {'woot': 'woot'}
        path = '/null/'
        headers = {'Whatever': 'woot'}
        operation = Operation.from_schema(Schema(SPEC), 'Null')
        self.assertEqual(True, operation.validate_request_body(body))
        self.assertEqual(True, operation.validate_request_query(query))
        self.assertEqual(True, operation.validate_request_path(path))
        self.assertEqual(True, operation.validate_request_headers(headers))

    def test_heterogenous_nested_collection_success(self):
        """
        Tests a heterogenous collection of items within a generic collection
        succeed when each individual item is well-formed with respect to it's
        discriminator.
        """
        body = {
            'items': [
                {
                    'type': 'CandyItem',
                    'color': 'red',
                },
                {
                    'type': 'BoogieItem',
                    'groove': 'funky',
                },
            ],
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateCollection')
        self.assertEqual(True, operation.validate_request_body(body))

    def test_heterogenous_nested_collection_error(self):
        """
        Tests that a heterogenous collection of items within a generic
        collection will return validation errors when one or more items is
        ill-formed with respect to it's discriminator.
        """
        body = {
            'items': [
                {
                    'type': 'CandyItem',
                    'color': 'red',
                },
                {
                    'type': 'BoogieItem',
                    # Expected error on invalid type.
                    'groove': 10,
                },
                {
                    'type': 'BoogieItem',
                    # Expected error on missing required param.
                },
            ],
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateCollection')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('items.1.groove', exc_info.exception.errors[0].field)
        self.assertEqual('items.2.groove', exc_info.exception.errors[1].field)

    def test_path_arg_extraction(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        successes = {
            # Correct format
            '/items/5': {
                'ItemID': '5',
            },
            # Almost the correct format but should still pass our intermediate
            # regexp.
            '/items/hello': {
                'ItemID': 'hello',
            },
            # Periods and nonesense
            '/items/.sfs2342': {
                'ItemID': '.sfs2342',
            },
            # Spaces
            '/items/%20things': {
                'ItemID': ' things',
            },
        }

        for case, expected in successes.iteritems():
            self.assertEqual(
                expected,
                operation.extract_path_args(case)
            )

    def test_path_validation_success(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        successes = {
            # Correct format
            '/items/5': True,
        }
        for case, expected in successes.iteritems():
            self.assertEqual(
                expected,
                operation.validate_request_path(case)
            )

    def test_path_validation_errors(self):
        operation = Operation.from_schema(Schema(SPEC), 'GetItem')
        errors = {
            '/items/der': 'ItemID',
            '/items/': 'ItemID',
        }
        for case, expected in errors.iteritems():
            with self.assertRaises(ValidationErrors) as exc_info:
                operation.validate_request_path(case)
            self.assertEqual(expected, exc_info.exception.errors[0].field)

    @patch('spectastic.operation.Operation.iter_request_header_errors')
    @patch('spectastic.operation.Operation.iter_request_body_errors')
    @patch('spectastic.operation.Operation.iter_request_path_errors')
    @patch('spectastic.operation.Operation.iter_request_query_errors')
    def test_validate_request(
        self, query_errors, path_errors, body_errors, header_errors
    ):
        """
        Ensures that we validate an entire request.
        """
        body = {'type': 'CandyItem', 'color': 'red'}
        encoded_body = json.dumps(body)
        headers = {
            'Authorization': 'bearer',
            'Content-Type': 'application/json',
        }
        query = {'unknown': 'param'}
        path = '/items/'

        request = BasicRequest(encoded_body, headers, query, path)
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        operation.validate_request(request)

        query_errors.assert_called_once_with(MultiDict(query))
        path_errors.assert_called_once_with(path)
        body_errors.assert_called_once_with(body)
        header_errors.assert_called_once_with(Headers(headers))

    def test_complex_allof_discriminator(self):
        """
        In cases like SweetCandyItem which extends CandyItem, which extends
        Item, we want to ensure things behave sensibly.
        """
        body = {
            'type': 'SweetCandyItem',
            'color': 'red',
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        with self.assertRaises(ValidationErrors) as exc_info:
            operation.validate_request_body(body)
        self.assertEqual('sweetness', exc_info.exception.errors[0].field)

    def test_discriminator_non_allof(self):
        """
        Regression test for discriminator's that are not within an allOf block.
        """
        body = {
            'type': 'Item',
        }
        operation = Operation.from_schema(Schema(SPEC), 'CreateItem')
        operation.validate_request_body(body)


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
