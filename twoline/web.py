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
    _, args = pipe().recv()
    logger.info('Received response %s', args)
    return args

@app.route('/message/', methods=['GET', 'POST'])
def message():
    if request.method == 'POST':
        response = send_and_receive(
            'add_message', request.data
        )
        return jsonify(
            id=response[0]
        )
    elif request.method == 'GET':
        response = send_and_receive(
            'get_messages', request.data
        )
        return jsonify(
            objects=response
        )
