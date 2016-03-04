import flask
from spectastic.contrib.flask_utils import validate_route
from spectastic.schema import Schema

from ..spec import SPEC
schema = Schema(SPEC)

app = flask.Flask(__name__)


def responder(*args):
    return flask.make_response('failed', 401, {'X-Sad': True})


@app.route('/items/<itemid>', methods=['GET'])
@validate_route(schema, 'GetItem', responder)
def get_item():
    return 'success'


@app.route('/items/', methods=['POST'])
@validate_route(schema, 'CreateItem')
def create_item():
    return 'success'
