import logging
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

    options, args = parser.parse_args()

    logging.basicConfig(
        level=logging.getLevelName(options.loglevel)
    )

    manager = Manager(*args, **vars(options))
    manager.run()
