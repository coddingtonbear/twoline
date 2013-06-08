from optparse import OptionParser


from twoline.manager import Manager


def run_from_cmdline():
    parser = OptionParser()
    parser.add_option(
        '--port', '-p', default=9101
    )

    options, args = parser.parse_args()

    manager = Manager(*args, **vars(options))
    manager.run()
