from functools import wraps
import logging
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

COMMANDS = {}


def command(fn):
    @wraps(fn)
    def wrapped(*args):
        self = args[0]
        logger.debug(
            'Executing %s%s',
            fn.func_name,
            args
        )
        response = fn(*args)
        logger.debug(
            'Response %s',
            response
        )
        if response:
            self.send_manager_data('response', response)
    COMMANDS[fn.func_name] = wrapped
    return fn


class LcdManager(object):
    def __init__(self, device_path, pipe):
        self.device = open(device_path, 'wb')
        self.pipe = pipe

        self.message = ''
        self.color = 0, 0, 0
        self.backlight = False

    def run(self):
        while True:
            if self.pipe.poll():
                cmd, args = self.pipe.recv()
                args.insert(0, self)
                if cmd in COMMANDS:
                    COMMANDS[cmd](*args)
                else:
                    logger.error(
                        'Received unknown command \'%s\' from manager.',
                        cmd
                    )
                    self.send_manager_data(
                        'error', 'Command %s does not exist' % cmd
                    )
            time.sleep(0.1)

    def send_manager_data(self, msg, data=None):
        if not data:
            data = []
        if not isinstance(data, (list, tuple)):
            data = [data, ]
        self.pipe.send((
            msg, data
        ))

    def send(self, cmd):
        self.device.write(cmd + '\n')

    @command
    def message(self, message):
        if 'message' in message and self.message != message['message']:
            self.set_message(message['message'])
        if message['color'] != self.color:
            self.set_backlight_color(message['color'])
        if message['backlight'] != self.backlight:
            if message['backlight']:
                self.on()
            else:
                self.off()

    @command
    def set_message(self, message):
        self.message = message
        self.send(message.encode('utf-8'))

    @command
    def off(self, *args):
        self.backlight = False
        self.send('\xfe\x46')

    @command
    def on(self, *args):
        self.backlight = True
        self.send('\xfe\x42')

    @command
    def clear(self, *args):
        self.message = ''
        self.send('\xfe\x58')

    @command
    def set_backlight_color(self, color):
        self.color = color
        self.send('\xfe\xd0%s%s%s' % tuple([chr(c) for c in color]))
