import logging
logger = logging.getLogger(__name__)

from functools import wraps
import json
import collections

# Flask is a test only dependency. We let people use this module without
# triggering a flask install.
try:
    import flask
except ImportError:
    logger.error(
        'You must have flask installed to use this optional module'
    )
    raise

from ..operation import Operation
from ..errors import ValidationErrors
from ..request import BasicRequest


def convert_request(flask_request):
    """
    Converts a flask :class:`flask.Request` to
    a :class:`~spectastic.request.BasicRequest`

    :return: :class:`~spectastic.request.BasicRequest`
    """
    return BasicRequest(
        flask.request.data,
        flask.request.headers,
        flask.request.args,
        flask.request.path,
    )


def default_responder(validation_errors):
    """
    Generates a flask response from provided ``validation_errors``.

    :param ~spectastic.errors.ValidationErrors validation_errors:
        A instance containing an aggregate of all errors discovered during
        request parsing.
    """
    response_body = {"errors": []}
    for error in validation_errors.errors:
        response_body['errors'].append({
            'msg': error.msg,
            'location': error.location,
            'field': error.field,
        })
    return flask.make_response(
        (json.dumps(response_body), 400, {'Content-Type': 'application/json'})
    )


def validate_route(schema, operation_id, responder=None):
    """
    :param ~spectastic.schema.Schema schema:
        The schema to use for validation. May also be a callable that receives
        a flask request and returns a :class:`~spectastic.schema.Schema`.
    :param string operation_id:
        The operation id to validate. May also be a callable that receives
        a flask request and returns a :class:`~spectastic.schema.Schema`.
    """
    def decorator(wrapped_func):
        @wraps(wrapped_func)
        def _decorated_function(*args, **kwargs):
            if responder is None:
                _responder = default_responder
            else:
                _responder = responder

            if _is_callable(schema):
                _schema = schema(flask.request)
            else:
                _schema = schema

            if _is_callable(operation_id):
                _operation_id = operation_id(flask.request)
            else:
                _operation_id = operation_id

            validation_response = _validate_route(
                _schema, _operation_id, _responder
            )
            if validation_response:
                return validation_response
            else:
                return wrapped_func(*args, **kwargs)
        return _decorated_function
    return decorator


def _validate_route(schema, operation_id, responder):
    """
    Broken out into a function for decorator testability.
    """
    operation = Operation.from_schema(schema, operation_id)
    try:
        operation.validate_request(convert_request(flask.request))
    except ValidationErrors as e:
        return responder(e)
    return


def _is_callable(value):
    """
    The method used by Python's 2-3 tool for detecting whether a value
    is callable.

    :return: bool
    """
    return isinstance(value, collections.Callable)
