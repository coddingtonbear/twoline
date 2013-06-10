import logging

from flask import Flask, request, jsonify


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
    logger.info('Received response %s', args)
    return args


@app.route('/', methods=['GET'])
def index():
    routes = {}
    for rule in app.url_map.iter_rules():
        routes[rule.endpoint] = {
            'url': rule.rule,
            'methods': list(rule.methods),
        }
    return jsonify(
        **routes
    )


@app.route('/contrast/', methods=['GET', 'PUT'])
def contrast():
    try:
        if request.method == 'GET':
            response = send_and_receive(
                'get_contrast'
            )
            return jsonify(
                contrast=response[0]
            )
        elif request.method == 'PUT':
            response = send_and_receive(
                'set_contrast', request.data
            )
            return jsonify(
                contrast=response[0]
            )
    except Exception as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 500
        return response


@app.route('/brightness/', methods=['GET', 'PUT'])
def brightness():
    try:
        if request.method == 'GET':
            response = send_and_receive(
                'get_brightness'
            )
            return jsonify(
                brightness=response[0]
            )
        elif request.method == 'PUT':
            response = send_and_receive(
                'set_brightness', request.data
            )
            return jsonify(
                brightness=response[0]
            )
    except Exception as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 500
        return response


@app.route('/message/', methods=['GET', 'POST'])
def message_list():
    try:
        if request.method == 'POST':
            response = send_and_receive(
                'post_message', request.data
            )
            return jsonify(
                **response[0]
            )
        elif request.method == 'GET':
            response = send_and_receive(
                'get_messages', request.data
            )
            return jsonify(
                objects=response
            )
    except HttpResponseBadRequest as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 400
        return response
    except Exception as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 500
        return response


@app.route('/flash/', methods=['GET', 'PUT', 'DELETE'])
def flash():
    try:
        if request.method == 'PUT':
            response = send_and_receive(
                'put_flash', request.data
            )
            return jsonify(
                **response[0]
            )
        elif request.method == 'DELETE':
            response = send_and_receive(
                'delete_flash'
            )
            return jsonify(
                status=response[0]
            )
        elif request.method == 'GET':
            response = send_and_receive(
                'get_flash'
            )
            return jsonify(
                **response[0]
            )
    except HttpResponseNotFound:
        response = jsonify(
            error='No flash message is currently set'
        )
        response.status_code = 404
        return response
    except HttpResponseBadRequest as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 400
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        response = jsonify(
            error=str(e)
        )
        response.status_code = 500
        return response


@app.route('/message/<message_id>/', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def message(message_id):
    try:
        if request.method == 'GET':
            response = send_and_receive(
                'get_message_by_id', message_id
            )
            return jsonify(
                **response[0]
            )
        elif request.method == 'DELETE':
            response = send_and_receive(
                'delete_message_by_id', message_id
            )
            return jsonify(
                status=response[0]
            )
        elif request.method == 'PUT':
            response = send_and_receive(
                'put_message_by_id', [message_id, request.data, ]
            )
            return jsonify(
                **response[0]
            )
        elif request.method == 'PATCH':
            response = send_and_receive(
                'patch_message_by_id', [message_id, request.data, ]
            )
            return jsonify(
                **response[0]
            )
    except HttpResponseNotFound:
        response = jsonify(
            error='Message ID %s does not exist' % message_id
        )
        response.status_code = 404
        return response
    except HttpResponseBadRequest as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 400
        return response
    except Exception as e:
        response = jsonify(
            error=str(e)
        )
        response.status_code = 500
        return response


class HttpResponse(Exception):
    pass


class HttpResponseNotFound(HttpResponse):
    pass


class HttpResponseBadRequest(HttpResponse):
    pass
