import datetime
from functools import wraps
import json
import logging
import multiprocessing
import time
import uuid

from dateutil.parser import parse
from dateutil.tz import tzlocal
from jsonschema import validate, ValidationError
import pytz

from twoline.exceptions import (
    InvalidRequest, NotFound, BadRequest, UnexpectedError
)
from twoline.lcd import LcdManager
from twoline.schema import message_schema, integer_schema
from twoline.web import app


logger = logging.getLogger(__name__)


WEB_COMMANDS = {}
LCD_COMMANDS = {}


def web_command(fn):
    @wraps(fn)
    def wrapped(*args):
        self = args[0]
        logger.debug(
            'Executing %s%s',
            fn.func_name,
            args
        )
        try:
            response = fn(*args)
            logger.debug(
                'Response %s',
                response
            )
            if response is not None:
                self.send_web_data('response', response)
        except NotFound as e:
            self.send_web_data('error', e)
        except ValidationError as e:
            self.send_web_data('error', InvalidRequest(str(e)))
        except ValueError as e:
            self.send_web_data('error', BadRequest(str(e)))
        except Exception as e:
            self.send_web_data('error', UnexpectedError(str(e)))

    WEB_COMMANDS[fn.func_name] = wrapped
    return wrapped


def lcd_command(fn):
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
        if response is not None:
            self.send_lcd_data('response', response)

    LCD_COMMANDS[fn.func_name] = wrapped
    return fn


class Manager(object):
    def __init__(
        self, device, ip='0.0.0.0', port=9101,
        size_x=16, size_y=2, blink_interval=0.25, text_cycle_interval=2,
        *args, **kwargs
    ):
        self.ip = ip
        self.port = port
        self.device = device
        self.size_x = int(size_x)
        self.size_y = int(size_y)
        self.blink_interval = float(blink_interval)
        self.text_cycle_interval = float(text_cycle_interval)

        self.web_pipe, self.web_proc = self.run_webserver()
        self.lcd_pipe, self.lcd_proc = self.run_lcd()

        self.no_messages = {
            'backlight': False,
            'message': ''
        }
        self.default_message = {
            'color': (255, 255, 255),
            'backlight': True,
            'interval': 5
        }
        self.default_flash = {
            'blink': [(255, 0, 0), (0, 0, 0)],
            'backlight': True,
            'timeout': 10
        }
        self.flash = None
        self.flash_until = None
        self.messages = []
        self._message_id = None
        self.until = None

        self.sleep = 0.2

    @property
    def message_id(self):
        return self._message_id

    @message_id.setter
    def message_id(self, value):
        logger.debug('Setting message_id to %s', self._message_id)
        self._message_id = value

    def run(self):
        logger.info(
            'Listening on http://%s:%s',
            self.ip,
            self.port
        )
        try:
            self._run()
        except Exception as e:
            logger.exception(e)
            try:
                self.lcd_proc.terminate()
            except Exception as e:
                logger.exception(e)
            try:
                self.web_proc.terminate()
            except Exception as e:
                logger.exception(e)

    def _run(self):
        logger.debug("Waiting for data")
        while True:
            if self.web_pipe.poll():
                cmd, args = self.web_pipe.recv()
                args.insert(0, self)
                logger.debug(
                    "Data received from WEB %s:%s",
                    cmd,
                    args
                )
                if cmd in WEB_COMMANDS:
                    logger.info(
                        'WEB Command Received %s%s',
                        cmd,
                        args
                    )
                    WEB_COMMANDS[cmd](*args)
                else:
                    logger.error(
                        'Received unknown command \'%s\' from web.',
                        cmd
                    )
                    self.send_web_data(
                        'error', 'Command %s does not exist' % cmd
                    )
            if self.lcd_pipe.poll():
                cmd, args = self.lcd_pipe.recv()
                args.insert(0, self)
                logger.debug(
                    "Data received from LCD %s:%s",
                    cmd,
                    args
                )
                if cmd in LCD_COMMANDS:
                    logger.info(
                        'LCD Command Received %s%s',
                        cmd,
                        args
                    )
                    WEB_COMMANDS[cmd](*args)
                else:
                    logger.error(
                        'Received unknown command \'%s\' from lcd.',
                        cmd
                    )
                    self.send_lcd_data(
                        'error', 'Command %s does not exist' % cmd
                    )
            time.sleep(self.sleep)
            self.update_screen()

    def get_flash_message(self):
        original_message = self.flash
        logger.debug("Original Flash: %s", original_message)
        default = self.default_flash.copy()
        default.update(
            original_message
        )
        logger.debug("Final Flash: %s", default)
        return default

    def get_message(self):
        if not self.message_id and self.messages:
            self.message_id = self.messages[0]['id']
        idx = self.get_message_index_by_id(self.message_id)
        original_message = self.messages[idx]
        logger.debug("Original Message: %s", original_message)
        default = self.default_message.copy()
        default.update(
            original_message
        )
        logger.debug("Final Message: %s", default)
        return default

    def get_no_messages_message(self):
        message = self.no_messages
        default = self.default_message.copy()
        default.update(
            message
        )
        return default

    def get_message_index_by_id(self, id_):
        for message in self.messages:
            if message['id'] == id_:
                return self.messages.index(message)

    def increment_index(self):
        if self.message_id:
            current_index = self.get_message_index_by_id(self.message_id) + 1
            if len(self.messages) <= current_index:
                current_index = 0
        else:
            current_index = 0
        self.until = None
        self.message_id = self.messages[current_index]['id']
        logger.debug(
            'Incrementing: Index: %s: %s',
            current_index,
            self.message_id
        )

    def delete_message(self, message_id):
        if self.message_id == message_id:
            self.increment_index()
            if self.message_id == message_id:
                # If we just incremented, and are still at the same index
                # there is only one message in the list, and we're
                # in the process of deleting it.
                self.until = None
                self.message_id = None
        idx = self.get_message_index_by_id(message_id)
        message = self.messages[idx]
        self.messages.remove(message)

    def handle_expirations(self):
        utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        for message in self.messages:
            if 'expires' in message and message['expires'] < utcnow:
                logger.info(
                    'Message %s has expired.',
                    message['id']
                )
                self.delete_message(message['id'])
        logger.debug('Flash Until: %s', self.flash_until)
        logger.debug('Message Until: %s', self.until)
        if self.flash and self.flash_until and self.flash_until < utcnow:
            logger.info('Flash message has expired')
            self.flash = None
            self.flash_until = None
        if self.messages:
            if self.until and self.until < utcnow:
                self.increment_index()

    def get_current_message(self):
        utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        self.handle_expirations()
        if self.flash:
            flash = self.get_flash_message()
            if not self.flash_until:
                self.flash_until = (
                    utcnow + datetime.timedelta(seconds=flash['timeout'])
                )
            return flash
        elif self.messages:
            message = self.get_message()
            if not self.until:
                self.until = (
                    utcnow + datetime.timedelta(seconds=message['interval'])
                )
            return message
        else:
            return self.get_no_messages_message()

    def update_screen(self):
        try:
            message = self.get_current_message()
        except TypeError:
            self.message_id = None
            message = None

        if not message:
            logger.warning(
                "Message was lost before it could be displayed; skipping."
            )
            return

        self.send_lcd_data(
            'message', message
        )

    def send_lcd_data(self, msg, data=None):
        if not data:
            data = []
        if not isinstance(data, (list, tuple)):
            data = [data, ]
        self.lcd_pipe.send((
            msg, data
        ))

    def send_web_data(self, msg, data=None):
        if not data:
            data = []
        if not isinstance(data, (list, tuple)):
            data = [data, ]
        self.web_pipe.send((
            msg, data
        ))

    def run_lcd(self):
        local, lcd_pipe = multiprocessing.Pipe()

        def _run_lcd():
            mgr = LcdManager(
                self.device,
                lcd_pipe,
                size_x=self.size_x,
                size_y=self.size_y,
                blink_interval=self.blink_interval,
                text_cycle_interval=self.text_cycle_interval
            )
            mgr.initialize()
            mgr.run()

        process = multiprocessing.Process(
            target=_run_lcd
        )
        process.start()
        logger.debug(
            'Started LCD on pid %s',
            process.pid
        )
        return local, process

    def run_webserver(self):
        local, webserver = multiprocessing.Pipe()

        def _run_webserver():
            app.config['PIPE'] = webserver
            app.run(
                host=self.ip,
                port=int(self.port),
            )
        process = multiprocessing.Process(
            target=_run_webserver
        )
        process.start()
        logger.debug(
            'Started WEB on pid %s',
            process.pid
        )
        return local, process

    def process_message(self, message, ignore_id=False):
        if 'expires' in message:
            if isinstance(message['expires'], datetime.datetime):
                message['expires'] = message['expires'].isoformat()
        validate(message, message_schema)
        if not 'id' in message or ignore_id:
            message['id'] = uuid.uuid4().hex
        if 'expires' in message:
            if isinstance(message['expires'], int):
                message['expires'] = (
                    datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
                    + datetime.timedelta(seconds=message['expires'])
                )
            elif isinstance(message['expires'], basestring):
                try:
                    expires = parse(message['expires'])
                    if not expires.tzinfo:
                        expires = expires.replace(tzinfo=tzlocal())
                    message['expires'] = expires
                except ValueError:
                    raise ValidationError(
                        (
                            '\'%s\' is neither a valid ISO datetime or an '
                            'integer count of seconds'
                        ) % message['expires']
                    )
            else:
                raise ValidationError(
                    (
                        '\'%s\' is neither a valid ISO datetime or an integer '
                        'count of seconds'
                    ) % message['expires']
                )
        return message

    @web_command
    def get_message_by_id(self, id_):
        idx = self.get_message_index_by_id(self.message_id)
        if idx is None:
            raise NotFound('Message %s does not exist' % id_)
        return self.messages[idx]

    @web_command
    def delete_message_by_id(self, id_):
        idx = self.get_message_index_by_id(self.message_id)
        if idx is None:
            raise NotFound('Message %s does not exist' % id_)
        self.delete_message(id_)
        return 'OK'

    @web_command
    def put_message_by_id(self, id_, message_payload):
        message = json.loads(message_payload)
        idx = self.get_message_index_by_id(self.message_id)
        if idx is None:
            message['id'] = id_
            self.messages.append(self.process_message(message))
            return message
        else:
            self.messages[idx] = self.process_message(message)
            self.messages[idx]['id'] = id_
            return self.messages[idx]

    @web_command
    def patch_message_by_id(self, id_, message_payload):
        message = json.loads(message_payload)
        idx = self.get_message_index_by_id(self.message_id)
        if idx is None:
            raise NotFound('Message %s does not exist' % id_)
        original_message = self.messages[idx]
        original_message.update(message)
        self.messages[idx] = self.process_message(original_message)
        return self.messages[idx]

    @web_command
    def set_brightness(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValidationError('Brightness requires an integer value')
        validate(value, integer_schema)
        self.send_lcd_data(
            'set_brightness', int(value)
        )
        return value

    @web_command
    def set_contrast(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValidationError('Contrast requires an integer value')
        validate(value, integer_schema)
        self.send_lcd_data(
            'set_contrast', int(value)
        )
        return value

    @web_command
    def get_messages(self, *args):
        return self.messages

    @web_command
    def post_message(self, message_payload):
        message = json.loads(message_payload)
        self.messages.append(
            self.process_message(
                message,
                ignore_id=True
            )
        )
        return message

    @web_command
    def put_flash(self, message_payload):
        self.flash = self.process_message(
            json.loads(
                message_payload
            )
        )
        return self.get_flash_message()  # Post-processing

    @web_command
    def delete_flash(self):
        self.flash = None
        self.flash_until = None
        return 'OK'

    @web_command
    def get_flash(self):
        if not self.flash:
            raise NotFound('Flash message not set')
        return self.flash

    @lcd_command
    @web_command
    def error(self, *args):
        print 'Error: %s' % [args]
