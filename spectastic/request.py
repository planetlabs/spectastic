import json

from werkzeug.datastructures import MultiDict, Headers


class BasicRequest(object):
    """
    Demonstrates the most basic interface required by spectastic for proper
    request validation.
    """
    def __init__(self, body, headers, query, path):
        """
        :param dict headers: A dictionary-like object of headers.
        :param dict query: A dictionary-like object of query parameters.
        :param dict body:
            Generally a json-encoded string, or JSON decoded dictionary.
        :param string path: The request path of the request.
        """

        if not hasattr(headers, 'iteritems'):
            raise ValueError('Headers are not dictionary-like')

        # Coerce headers and query.
        headers = Headers(headers)
        query = MultiDict(query)

        if not hasattr(query, 'iteritems'):
            raise ValueError('Query is not dictionary-like')

        if 'content-type' in headers:
            value = headers['content-type']
            if value == 'application/json':
                if isinstance(body, basestring) and body == '':
                    body = None
                elif isinstance(body, basestring):
                    try:
                        body = json.loads(body)
                    except:
                        raise ValueError((
                            'Body could not be parsed as '
                            'json despite content-type'
                        ))

        self.headers = headers
        self.body = body
        self.query = query
        self.path = path
