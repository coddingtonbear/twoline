from functools import wraps
import logging
import re
import time

import six

from .exceptions import LcdCommandError


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


class CallableLcdCommand(object):
    def __init__(self, manager, command):
        self._manager = manager
        self._command = command

    def __call__(self, *args):
        result = self._command(*args)
        self._manager.send(result)


@six.python_2_unicode_compatible
class LcdCommand(object):
    COMMAND_PREFIX = '\xfe'

    def __init__(self, byte, args=None, prefix='\n'):
        if args is None:
            args = []

        self._byte = byte
        self._args = args
        self._prefix = prefix

    def build_command(self, *args):
        cmd = self.COMMAND_PREFIX

        if len(args) != len(self._args):
            raise LcdCommandError(
                "Argument count mismatch; expected {expected}, but "
                "only {actual} were received.".format(
                    expected=len(self._args),
                    actual=len(args),
                )
            )

        cmd += self._byte

        for idx, processor in enumerate(self._args):
            arg = args[idx]
            cmd += str(processor(arg))

        return cmd

    def __call__(self, *args):
        return self.build_command(*args)

    def __str__(self):
        return u'LCD Command "{command}"'.format(
            command=self._byte.encode('string-escape')
        )


@six.python_2_unicode_compatible
class LcdClient(object):
    COMMANDS = {
        'on': LcdCommand('\x42', args=[chr]),
        'off': LcdCommand('\x46'),
        'set_brightness': LcdCommand('\x99', args=[chr]),
        'set_contrast': LcdCommand('\x50', args=[chr]),
        'enable_autoscroll': LcdCommand('\x51'),
        'disable_autoscroll': LcdCommand('\x52'),
        'clear': LcdCommand('\x58'),
        'set_splash_screen': LcdCommand('\x40', args=[str]),
        'set_cursor_position': LcdCommand('\x47', args=[chr, chr]),
        'cursor_home': LcdCommand('\x48', prefix=''),
        'cursor_backward': LcdCommand('\x4c', prefix=''),
        'cursor_forward': LcdCommand('\x4d', prefix=''),
        'cursor_underline_on': LcdCommand('\x4a', prefix=''),
        'cursor_underline_off': LcdCommand('\x4b', prefix=''),
        'cursor_block_on': LcdCommand('\x53', prefix=''),
        'cursor_block_off': LcdCommand('\x54', prefix=''),
        'set_backlight_color': LcdCommand('\xd0', args=[chr, chr, chr]),
        'set_lcd_size': LcdCommand('\xd1', args=[chr, chr]),
        'gpo_off': LcdCommand('\x56'),
        'gpo_on': LcdCommand('\x57'),
    }

    def __init__(self, device_path):
        self.device_path = device_path

    def __getattr__(self, name):
        if name not in self.COMMANDS:
            raise AttributeError(name)

        return CallableLcdCommand(self, self.COMMANDS[name])

    def send(self, cmd):
        logger.debug(
            'Sending command: "%s"' % cmd.encode('string-escape')
        )
        try:
            with open(self.device_path, 'wb') as dev:
                dev.write(cmd)
        except IOError:
            logger.error(
                'Device unavailable; command \'%s\' dropped.',
                cmd
            )

    def send_text(self, text):
        self.send(text.encode('ascii', 'replace'))

    def __str__(self):
        return 'LCD Screen at {path}'.format(path=self.device_path)


class LcdManager(object):
    def __init__(
        self, device_path, pipe=None, size=None,
        blink_interval=0.25, text_cycle_interval=2, size_x=16, size_y=2
    ):
        self.client = LcdClient(device_path)

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
        self.client.disable_autoscroll()
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

        self.client.cursor_home()
        cleaned_lines = [
            line.ljust(self.size[0])
            for line in self.message_lines[
                self.text_idx:self.text_idx+self.size[1]
            ]
        ]
        display_text = ''.join(cleaned_lines)[0:self.size[0]*self.size[1]]
        if not display_text:
            self.off()
        self.client.send_text(display_text)
        self.text_idx += 2

    def handle_blink(self):
        if not self.blink:
            return
        self.blink_idx += 1
        if len(self.blink) <= self.blink_idx:
            self.blink_idx = 0
        self.client.set_backlight_color(
            *self.blink[self.blink_idx]
        )

    def send_manager_data(self, msg, data=None):
        if not data:
            data = []
        if not isinstance(data, (list, tuple)):
            data = [data, ]
        self.pipe.send((
            msg, data
        ))

    def get_message_lines(self, message):
        lines = []
        original_lines = re.split('\r|\n', message)
        for line in original_lines:
            lines.extend(
                line[i:i+self.size[0]]
                for i in range(0, len(line), self.size[0])
            )
        return lines

    @command
    def set_contrast(self, value):
        logger.debug('Setting contrast to %s', value)
        self.client.set_contrast(value)

    @command
    def set_brightness(self, value):
        logger.debug('Setting brightness to %s', value)
        self.client.set_brightness(value)

    @command
    def message(self, message):
        backlight = message.get('backlight', True)
        text = message.get('message', '')
        blink = message.get('blink', [])
        color = message.get('color', [255, 255, 255])

        # If the backlight is off, just turn it off and be done with it.
        if not backlight:
            self.off()
            return

        if self.message != text:
            self.set_message(text)

        if blink and self.blink != blink:
            self.set_blink(blink)
        if not blink:
            self.set_blink([])
        if (
            not self.blink and
            color != self.color
        ):
            self.set_backlight_color(color)

        if backlight != self.backlight:
            if backlight:
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
        self.client.off()

    @command
    def on(self, *args):
        logger.debug('Setting backlight to on')
        self.backlight = True
        self.client.on(255)

    @command
    def clear(self, *args):
        self.message = ''
        self.text_idx = 0
        self.message_lines = []
        self.client.clear()

    @command
    def set_backlight_color(self, color):
        logger.debug('Setting backlight color to %s', color)
        self.color = color
        self.client.set_backlight_color(*color)
