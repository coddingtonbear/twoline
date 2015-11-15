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
    def __init__(self, device_path, pipe=None, size=None,
            blink_interval=0.25, text_cycle_interval=2, size_x=16, size_y=2):
        self.device_path = device_path
        self.pipe = pipe
        if not size:
            size = [16, 2]
        self.size = size

        self.message = ''
        self.message_lines = []
        self.color = 0, 0, 0
        self.backlight = True

        self.sleep = 0.1

        self.blink = []
        self.blink_idx = 0
        self.blink_counter = 0
        self.blink_interval = int(
            (1.0 / self.sleep) * blink_interval
        )

        self.text_idx = 0
        self.text_cycle_counter = 0
        self.text_cycle_interval = int(
            (1.0 / self.sleep) * text_cycle_interval
        )

    def initialize(self):
        self.send('\xfe\x52')
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
            if self.text_cycle_counter >= self.text_cycle_interval:
                self.text_cycle_counter = 0
                self.handle_text_cycle()
            else:
                self.text_cycle_counter += 1
            time.sleep(self.sleep)

    def handle_text_cycle(self):
        if len(self.message_lines) <= self.text_idx:
            self.text_idx = 0
        self.send('\xfe\x58')
        self.send('\xfe\x4700')
        cleaned_lines = [
            line.ljust(self.size[0])
            for line in self.message_lines[
                self.text_idx:self.text_idx+self.size[1]
            ]
        ]
        display_text = ''.join(cleaned_lines)[0:self.size[0]*self.size[1]-1]
        self.send(display_text.encode('ascii', 'replace'))
        if not display_text:
            self.off()
        self.text_idx += 2

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

    def send_raw(self, cmd):
        with open(self.device_path, 'w') as dev:
            dev.write(cmd)

    def send(self, cmd):
        try:
            cmd = cmd + '\n'
            logger.debug(
                'Sending command: "%s"' % cmd.encode('string-escape')
            )
            self.send_raw(cmd)
        except IOError:
            logger.error(
                'Device unavailable; command \'%s\' dropped.',
                cmd
            )

    def get_message_lines(self, message):
        lines = []
        original_lines = message.split('\r')
        for line in original_lines:
            lines.extend(
                line[i:i+self.size[0]]
                for i in range(0, len(line), self.size[0])
            )
        logger.debug(lines)
        return lines

    @command
    def set_contrast(self, value):
        logger.debug('Setting contrast to %s', value)
        self.send('\xfe\x50%s' % chr(value))

    @command
    def set_brightness(self, value):
        logger.debug('Setting brightness to %s', value)
        self.send('\xfe\x99%s' % chr(value))

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

    @command
    def set_blink(self, colors):
        self.blink = colors
        self.blink_idx = 0
        if self.blink:
            self.set_backlight_color(self.blink[self.blink_idx])

    @command
    def set_message(self, message):
        logger.debug('Setting message \'%s\'', message)
        self.clear()
        self.text_idx = 0
        self.message = message.replace('\n', '')
        self.message_lines = self.get_message_lines(self.message)
        self.handle_text_cycle()

    @command
    def off(self, *args):
        logger.debug('Setting backlight to off')
        self.backlight = False
        self.send('\xfe\x46')

    @command
    def on(self, *args):
        logger.debug('Setting backlight to on')
        self.backlight = True
        self.send('\xfe\x42')

    @command
    def clear(self, *args):
        self.message = ''
        self.text_idx = 0
        self.message_lines = []
        self.send('\xfe\x58')

    @command
    def set_backlight_color(self, color):
        logger.debug('Setting backlight color to %s', color)
        self.color = color
        self.send('\xfe\xd0%s%s%s' % tuple([chr(c) for c in color]))
