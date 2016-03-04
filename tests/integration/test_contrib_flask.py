from mock import patch
import json
import unittest

from spectastic.contrib.flask_utils import validate_route
from spectastic.schema import Schema

from .app import app
from ..spec import generate_schema


class TestFlaskDecorator(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_validation(self):
        response = self.app.post(
            '/items/',
            data='{"sdfs": "sdfs"}',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEquals(400, response.status_code)

        payload = json.loads(response.data)
        self.assertEquals(payload, {
            'errors': [
                {
                    "location": "body",
                    "msg": "'type' is a required property",
                    "field": "type",
                },
                {
                    "location": "header",
                    "msg": "Required header is missing",
                    "field": "Authorization",
                },
            ],
        })

    def test_responder(self):
        for case in [3, 'dsds', '%20', '  ']:
            response = self.app.get(
                '/items/{}'.format(case),
            )
            self.assertEquals(401, response.status_code)
            self.assertEquals('failed', response.data)
            self.assertIn("X-Sad", response.headers)

    @patch('flask.request')
    @patch('spectastic.contrib.flask_utils._validate_route')
    def test_callable_schema(self, mock_validate, mock_request):
        foo = Schema(generate_schema())
        bar = Schema(generate_schema())
        for spec in [foo, bar]:
            callable = lambda *args: spec

            @validate_route(callable, 'Get')
            def get(*args):
                return 'foobar'
            get('')

    @patch('flask.request')
    @patch('spectastic.contrib.flask_utils._validate_route')
    def test_callable_operation(self, mock_validate, mock_request):
        bar = Schema(generate_schema())
        for operation_id in ['Foo', 'Bar']:
            callable = lambda *args: operation_id

            @validate_route(bar, callable)
            def get(*args):
                return 'foobar'
            get('')
            self.assertEqual(operation_id, mock_validate.call_args[0][1])
            self.assertEqual(operation_id, mock_validate.call_args[0][1])
