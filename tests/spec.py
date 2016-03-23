import json


SPEC = {
    'basePath': '/',
    'consumes': [
        'application/json',
    ],
    'info': {
        'description': 'A schema to drive integration tests',
        'version': '0.0.1',
        'title': 'spectastic Test Schema',
    },
    'parameters': {
        'qSearch': {
            'description': 'A search query',
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'required': True,
        },
        'pItemID': {
            'description': 'The ID of the Item',
            'name': 'ItemID',
            'in': 'path',
            'type': 'number',
            'format': 'integer',
            'required': True,
        },
        'pAuthorization': {
            'description': 'The authorization header',
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
        },
    },
    'definitions': {
        # Extension
        'Error': {
            'description': 'A generic error',
            'properties': {
                'msg': {
                    'type': 'string',
                },
            },
        },
        'NastyError': {
            'description': 'A generic error',
            'allOf': [
                {'$ref': '#/definitions/Error'},
                {
                    'properties': {
                        'insult': {
                            'type': 'string',
                        },
                    },
                },
            ],
        },
        # Polymorphism
        'Item': {
            'description': 'An abstract thing of some sort',
            'properties': {
                'type': {
                    'type': 'string',
                    'pattern': '[a-zA-Z]{1,16}',
                },
            },
            'discriminator': 'type',
            'required': ['type'],
        },
        'ItemCollection': {
            'description': 'A collection of Items',
            'properties': {
                'items': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/definitions/Item',
                    },
                },
            },
            'required': ['items'],
        },
        'CandyItem': {
            'description': 'An Item that is actually candy, congrats',
            'allOf': [
                {'$ref': '#/definitions/Item'},
                {
                    'properties': {
                        'color': {
                            'type': 'string',
                        },
                    },
                    'required': ['color'],
                },
            ],
        },
        'BoogieItem': {
            'description': 'An Item that knows how to boggie',
            'allOf': [
                {'$ref': '#/definitions/Item'},
                {
                    'properties': {
                        'groove': {
                            'type': 'string',
                        },
                    },
                    'required': ['groove'],
                },
            ],
        },
        'SweetCandyItem': {
            'description': 'A candy item that is sweet.',
            'allOf': [
                {'$ref': '#/definitions/CandyItem'},
                {
                    'properties': {
                        'sweetness': {
                            'type': 'string',
                        },
                    },
                    'required': ['sweetness'],
                },
            ],
        },
    },
    'paths': {
        # Path parameters, multiple methods, and body parameters.
        '/items/{ItemID}': {
            'get': {
                'description': 'Get an Item',
                'operationId': 'GetItem',
                'parameters': [
                    {'$ref': '#/parameters/pItemID'},
                    {'$ref': '#/parameters/pAuthorization'}
                ],
                'responses': {
                    '200': {
                        'description': 'Successful obtained an Item',
                        'schema': {
                            '$ref': '#/definitions/Item',
                        },
                    },
                },
            },
        },
        # Non-mandatory query parameter.
        # Mandatory header.
        '/items/': {
            'get': {
                'description': 'Get all items',
                'operationId': 'GetItems',
                'parameters': [],
                'responses': {
                    '200': {
                        'description': 'Successful Item listing',
                        'schema': {
                            '$ref': '#/definitions/ItemCollection',
                        }
                    }
                }
            },
            'post': {
                'description': 'Create an Item',
                'operationId': 'CreateItem',
                'parameters': [
                    {'$ref': '#/parameters/pAuthorization'},
                    {
                        'in': 'body',
                        'name': 'item',
                        'required': True,
                        'schema': {
                            '$ref': '#/definitions/Item'
                        },
                    },
                ],
                'responses': {
                    '201': {
                        'description': 'Successful Item Creation',
                        'headers': {
                            'Location': {
                                'type': 'string',
                            },
                        },
                        'schema': {
                            '$ref': '#/definitions/Item',
                        },
                    },
                },
            },
        },
        '/itemcollection/': {
            'post': {
                'description': 'Create an item collection',
                'operationId': 'CreateCollection',
                'parameters': [
                    {
                        'in': 'body',
                        'name': 'itemcollection',
                        'required': True,
                        'schema': {
                            '$ref': '#/definitions/ItemCollection'
                        },
                    },
                ],
                'responses': {
                    '200': {
                        'description': 'Successful ItemCollection creation',
                        'schema': {
                            '$ref': '#/definitions/ItemCollection',
                        },
                    },
                },
            }
        },
        # Mandatory query parameter.
        '/search/': {
            'get': {
                'description': 'Search for things',
                'operationId': 'Search',
                'parameters': [
                    {'$ref': '#/parameters/qSearch'}
                ],
                'responses': {
                    '200': {
                        'description': 'Success item search.',
                        'schema': {
                            '$ref': '#/definitions/ItemCollection',
                        }
                    }
                }
            },
        },
        # No params
        '/null': {
            'get': {
                'description': 'Do nothing, validate nothing.',
                'operationId': 'Null',
                'parameters': [],
                'responses': {
                    '200': {
                        'description': 'Did nothing',
                    }
                },
            },
        },
    },
    'swagger': '2.0',
}


def generate_param(name, location, _type, required=None, _format=None):
    """
    Generates a parameter definition dynamically.
    """
    param = {
        'in': location,
        'type': _type,
        'name': name,
    }

    if required is not None:
        param['required'] = required

    if _format is not None:
        param['format'] = _format

    return param


def generate_method(
    path="/",
    method="get",
    responses=None,
    operation_id="Get",
    parameters=None,
):
    """
    Generates the method portion of a schema for testing purposes.
    """
    if responses is None:
        responses = {"200": {"description": "OK"}}
    if parameters is None:
        parameters = []

    return {
        path: {
            method: {
                "description": "Test method",
                "operationId": operation_id,
                "parameters": parameters,
                "responses": responses,
            },
        },
    }


def generate_schema(methods=None, base_path='/'):
    """
    Generates a schema dynamically. Uses a default method at the path "/"
    if no methods are specified.
    """
    if methods is None:
        methods = generate_method()
    base = {
        'basePath': base_path,
        'consumes': [
            'application/json',
        ],
        'info': {
            'description': 'A schema to drive integration tests',
            'version': '0.0.1',
            'title': 'spectastic Test Schema',
        },
        'swagger': '2.0',
        'paths': methods,
    }
    return base


if __name__ == '__main__':
    print json.dumps(SPEC, indent=2)
