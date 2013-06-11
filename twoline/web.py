import datetime
import json
import logging

from flask import Flask, make_response, request

from twoline.exceptions import InvalidRequest, NotFound, BadRequest


logger = logging.getLogger(__name__)


app = Flask(__name__)


def pipe():
    return app.config['PIPE']


def send_data(msg, data=None):
    if not data:
        data = []
    if not isinstance(data, (list, tuple)):
        data = [data, ]
    logger.debug(
        'Sending data %s%s',
        msg,
        data
    )
    pipe().send((
        msg, data
    ))


def send_and_receive(msg, data=None):
    send_data(msg, data)
    while not pipe().poll():
        pass
    t, args = pipe().recv()
    if t == 'error':
        logger.error('Received error response %s', args)
        raise args[0]
    logger.debug('Received response %s', args)
    return args


def json_response(status_code=200, **kwargs):
    def handle_data(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError
    response = make_response(
        json.dumps(
            kwargs,
            default=handle_data,
            indent=2
        ),
        status_code
    )
    response.status_code = status_code
    response.headers['Content-Type'] = 'application/json'
    return response


@app.errorhandler(Exception)
def exception_handler(e):
    status_code = 500
    if isinstance(e, InvalidRequest):
        status_code = 422
    elif isinstance(e, NotFound):
        status_code = 404
    elif isinstance(e, BadRequest):
        status_code = 400
    return json_response(
        status_code=status_code,
        error=str(e)
    )


for error in range(400, 599):
    @app.errorhandler(error)
    def error(e):
        return json_response(
            status_code=e.code,
            error=str(e)
        )


@app.route('/', methods=['GET'])
def index():
    routes = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint in ('index', 'static'):
            continue
        routes[rule.endpoint] = {
            'url': rule.rule,
            'methods': list(rule.methods),
        }
    return json_response(
        **routes
    )


@app.route('/contrast/', methods=['GET', 'PUT'])
def contrast():
    if request.method == 'GET':
        response = send_and_receive(
            'get_contrast'
        )
        return json_response(
            contrast=response[0]
        )
    elif request.method == 'PUT':
        response = send_and_receive(
            'set_contrast', request.data
        )
        return json_response(
            contrast=response[0]
        )


@app.route('/brightness/', methods=['GET', 'PUT'])
def brightness():
    if request.method == 'GET':
        response = send_and_receive(
            'get_brightness'
        )
        return json_response(
            brightness=response[0]
        )
    elif request.method == 'PUT':
        response = send_and_receive(
            'set_brightness', request.data
        )
        return json_response(
            brightness=response[0]
        )


@app.route('/message/', methods=['GET', 'POST'])
def message_list():
    if request.method == 'POST':
        response = send_and_receive(
            'post_message', request.data
        )
        return json_response(
            status_code=201,
            **response[0]
        )
    elif request.method == 'GET':
        response = send_and_receive(
            'get_messages', request.data
        )
        return json_response(
            messages=response
        )


@app.route('/flash/', methods=['GET', 'PUT', 'DELETE'])
def flash():
    if request.method == 'PUT':
        response = send_and_receive(
            'put_flash', request.data
        )
        return json_response(
            status_code=201,
            **response[0]
        )
    elif request.method == 'DELETE':
        response = send_and_receive(
            'delete_flash'
        )
        return json_response(
            status=response[0]
        )
    elif request.method == 'GET':
        response = send_and_receive(
            'get_flash'
        )
        return json_response(
            **response[0]
        )


@app.route('/message/<message_id>/', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def message(message_id):
    if request.method == 'GET':
        response = send_and_receive(
            'get_message_by_id', message_id
        )
        return json_response(
            **response[0]
        )
    elif request.method == 'DELETE':
        response = send_and_receive(
            'delete_message_by_id', message_id
        )
        return json_response(
            status=response[0]
        )
    elif request.method == 'PUT':
        response = send_and_receive(
            'put_message_by_id', [message_id, request.data, ]
        )
        return json_response(
            status_code=201,
            **response[0]
        )
    elif request.method == 'PATCH':
        response = send_and_receive(
            'patch_message_by_id', [message_id, request.data, ]
        )
        return json_response(
            **response[0]
        )
