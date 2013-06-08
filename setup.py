import multiprocessing

from setuptools import setup

setup(
    name='twoline',
    version='0.0.1',
    url='http://bitbucket.org/latestrevision/twoline/',
    description='Manager for two-line LCDs',
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    packages=['twoline', ],
    entry_points={'console_scripts': [
        'twoline = twoline.cmdline:run_from_cmdline']},
    test_suite='nose.collector',
    tests_require=[
        'nose',
    ]
)
