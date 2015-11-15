import json
import logging.config
from optparse import OptionParser

from twoline.manager import Manager


def run_from_cmdline():
    parser = OptionParser()
    parser.add_option(
        '--port', '-p', dest='port', default='6224'
    )
    parser.add_option(
        '--ip', '-i', dest='ip', default='0.0.0.0'
    )
    parser.add_option(
        '--loglevel', '-l', dest='loglevel', default='INFO'
    )
    parser.add_option(
        '--logcfg', dest='logcfg', default=None
    )
    parser.add_option(
        '--size-x', '-x', dest='size_x', default='16',
    )
    parser.add_option(
        '--size-y', '-y', dest='size_y', default='2',
    )
    parser.add_option(
        '--text-cycle-interval', dest='text_cycle_interval', default='2'
    )
    parser.add_option(
        '--blink-interval', dest='blink_interval', default='0.25'
    )

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Device required (usually a path in /dev/)')

    if options.logcfg:
        with open(options.logcfg, 'r') as in_:
            logging.config.dictConfig(
                json.loads(in_.read())
            )
    else:
        logging.basicConfig(
            level=logging.getLevelName(options.loglevel)
        )

    manager = Manager(*args, **vars(options))
    manager.run()
