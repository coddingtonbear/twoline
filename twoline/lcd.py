from functools import wraps
import logging
import time


logger = logging.getLogger(__name__)


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
    def __init__(self, device_path, pipe, size=None):
        self.device = open(device_path, 'wb')
        self.pipe = pipe
        if not size:
            size = [16, 2]
        self.size = size

        self.message = ''
        self.message_lines = []
        self.color = 0, 0, 0
        self.blink = []
        self.blink_idx = 0
        self.backlight = True

        self.sleep = 0.1
        self.blink_counter = 0
        self.blink_interval = int((1.0 / self.sleep) / 4.0)

        self.clear()

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
            if self.blink_counter >= self.blink_interval:
                self.blink_counter = 0
                self.handle_blink()
            else:
                self.blink_counter += 1
            time.sleep(self.sleep)

    def handle_blink(self):
        if not self.blink:
            return
        self.blink_idx += 1
        if len(self.blink) <= self.blink_idx:
            self.blink_idx = 0
        self.set_backlight_color(self.blink[self.blink_idx])

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
        if 'blink' in message and self.blink != message['blink']:
            self.set_blink(message['blink'])
        if not 'blink' in message:
            self.set_blink([])
        if not self.blink and message['color'] != self.color:
            self.set_backlight_color(message['color'])
        if message['backlight'] != self.backlight:
            if message['backlight']:
                self.on()
            else:
                self.off()

    def get_message_lines(self, message):
        lines = message.split('\r')
        return lines

    @command
    def set_blink(self, colors):
        self.blink = colors
        self.blink_idx = 0
        if self.blink:
            self.set_backlight_color(self.blink[self.blink_idx])

    @command
    def set_message(self, message):
        logger.info('Setting message \'%s\'', message)
        self.clear()
        self.message = message.replace('\n', '')
        self.message_lines = self.get_message_lines(self.message)
        self.send(message.encode('utf-8'))

    @command
    def off(self, *args):
        logger.info('Backlight Off')
        self.backlight = False
        self.send('\xfe\x46')

    @command
    def on(self, *args):
        logger.info('Backlight On')
        self.backlight = True
        self.send('\xfe\x42')

    @command
    def clear(self, *args):
        self.message = ''
        self.message_lines = []
        self.send('\xfe\x58')

    @command
    def set_backlight_color(self, color):
        logger.info('Setting backlight to %s', color)
        self.color = color
        self.send('\xfe\xd0%s%s%s' % tuple([chr(c) for c in color]))
