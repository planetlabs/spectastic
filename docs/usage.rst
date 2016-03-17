============
Basic Usage
============

To use Spectastic in a project::

    import spectastic

First, it's important to know that spectastic assumes that it's working with
a valid Open API / Swagger schema to reduce it's dependency footprint. If
you need to validate your schema, consider
`bravado-core <https://github.com/Yelp/bravado-core>`_.

.. warning::
  You'll want to make sure you've specified ``operation id's`` for all paths.
  These aren't mandatory in an Open API specification, but are mandatory for
  spectastic.

Validating Incoming Requests
----------------------------

Spectastic offers two strategies for validation:

* Iterative API's that yield individual :class:`~spectastic.errors.FieldError`
  instances.
* :class:`~spectastic.errors.ValidationErrors` raising methods.

Most of spectastic's utility is contained within
:class:`~spectastic.operation.Operation` instances. Lets make one using our
`test schema <https://gitub.com/planetlabs/spectastic/tests/schema.py>`_::

    from spectastic.schema import Schema
    from spectastic import Operation

    schema = Spec(SPEC)
    op = Operation.from_schema(schema, 'GetItem')

Once instantiated, you can validate an incoming
:class:`~spectastic.request.BasicRequest`::

    op.validate_request(request)

.. note::
  :class:`~spectastic.request.BasicRequest` is probably not what you're using
  in your app. If you're using **flask**, check out
  :func:`~spectastic.contrib.flask_utils.convert_request` to make the
  conversion.


If there are validation errors, we'll raise a :class:`~spectastic.errors.ValidationErrors`
exception, which contains an ``errors`` property consisting of a list of
:class:`~spectastic.errors.FieldError`::

    from spectastic.request import BasicRequest

    request = BasicRequest(
        {"hello": "world"},
        {"Authorization": "basic beefbabaabbabeef"},
        {"query": "created:yesterday"},
        "/things/are/great",
    )

    try:
      op.validate_request(request)
    except ValidationErrors as e:
      print e.errors[0].field

.. note::
  Though it works out of the box, strictly speaking the request doesn't need
  to be a werkzeug Request. See :class:`~spectastic.request.BasicRequest` for
  an example.

  Spectastic is :class:`~werkzeug.datastructures.MultiDict` and
  :class:`~werkzeug.datastructures.Headers` aware. These data structures
  facilitate query parameters / headers that occur multiple times in a request
  e.g. a query such as "http://example.com?search=foo&search=bar".

Flask Integration
-----------------

Spectastic's :mod:`~spectastic.contrib.flask_utils` module has some additional
tools to automatically validate incoming requests for a given route against
your schema::


  from spectastic.contrib.flask_utils import validate_route

  ...

  @validate_route(schema, 'GetItems')
  @app.route('/items/')
  def get_items(*args, **kwargs):
    return 'Success'

The :func:`~spectastic.contrib.flask_utils.validate_route` function has a few
bonuses. The first argument may be a :class:`~spectastic.schema.Schema`
instance or a callable that returns a Schema. An optional ``responder``
callable receives any :class:`~spectastic.errors.ValidationErrors` that may
have occured and returns an appropriate flask-compatible response. You can use
this to customize your error output.

The :func:`~spectastic.contrib.flask_utils.default_responder` simply outputs
the general structure shown below along with a 400 status code::

    {
      "errors": [
        {
          "msg": "Required path parameter is missing",
          "location": "path",
          "field": "query",
        },
        {
          ...
        }
      ]
    }
