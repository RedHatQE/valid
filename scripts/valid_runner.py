#! /usr/bin/python -tt
"""
Validation runner
"""

import multiprocessing
import time
import logging
from valid.logging_customizations import ValidLogger
logging.setLoggerClass(ValidLogger)
import argparse
import sys

sys.path.insert(0, ".")
from valid import valid_main


def csv(value):
    """
    Generate list from comma-separated value

    @param value: comma-separated value
    @type value: string

    @return: list of values
    @rtype: list of str
    """
    return [str(val) for val in value.split(',')]


def logArgType(value):
    """
    figure out logging level from value

    @return: logging.<LEVEL>
    @rtype: type(logging.<LEVEL>)
    """
    level = getattr(logging, value.upper(), logging.NOTSET)
    return level
            
    


runner = valid_main.ValidMain()

# pylint: disable=C0103,E1101
argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--data', help='data file for validation')
argparser.add_argument('--config',
                       default=runner.config, help='use supplied yaml config file')
argparser.add_argument('--loglevel', type=logArgType, default=logging.PROGRESS,
                        help='set logging level')

argparser.add_argument('--disable-stages', type=csv, help='disable specified stages')
argparser.add_argument('--enable-stages', type=csv, help='enable specified stages (overrides --disable-stages)')

argparser.add_argument('--disable-tests', type=csv, help='disable specified tests')
argparser.add_argument('--enable-tests', type=csv, help='enable specified tests only (overrides --disabe-tests)')

argparser.add_argument('--disable-tags', type=csv, help='disable specified tags')
argparser.add_argument('--enable-tags', type=csv, help='enable specified tags only (overrides --disabe-tags)',
                       default='default')

argparser.add_argument('--repeat', type=int, help='repeat testing with the same instance N times',
                       default=runner.repeat)

argparser.add_argument('--maxtries', type=int,
                       default=runner.maxtries, help='maximum number of tries')
argparser.add_argument('--maxwait', type=int,
                       default=runner.maxwait, help='maximum wait time for instance creation')

argparser.add_argument('--minprocesses', type=int,
                       default=runner.minprocesses, help='minimum number of worker processes')
argparser.add_argument('--maxprocesses', type=int,
                       default=runner.maxprocesses, help='maximum number of worker processes')

argparser.add_argument('--results-dir',
                       default=False, help='put resulting yaml files to specified location')
argparser.add_argument('--server', action='store_const', const=True,
                       default=False, help='run HTTP server')
argparser.add_argument('--settlewait', type=int,
                       default=runner.settlewait, help='wait for instance to settle before testing')
argparser.add_argument('--hwp-filter', help='select hwps to instantiate',
                       default=runner.hwp_filter)

argparser.add_argument('--no-action', '-n', help='Do not run tests, just list what would be done otherwise',
                        action='store_true')

args = argparser.parse_args()
runner.loglevel = args.loglevel
if not args.server:
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
else:
    # We use systemd-journald, skip date-time
    if args.loglevel == logging.DEBUG:
        logging.basicConfig(format='%(levelname)s %(message)s')
    else:
        # skip loglevel as well
        logging.basicConfig(format='%(message)s')
logger = logging.getLogger('valid.runner')

runner.maxtries = args.maxtries
runner.maxwait = args.maxwait
runner.settlewait = args.settlewait

runner.minprocesses = args.minprocesses
runner.maxprocesses = args.maxprocesses

if args.config:
    runner.config = args.config

if args.results_dir:
    runner.resdir = args.results_dir

if args.enable_tests:
    runner.enable_tests = set(args.enable_tests)

if args.disable_tests:
    runner.disable_tests = set(args.disable_tests)

if args.enable_stages:
    runner.enable_stages = set(args.enable_stages)

if args.disable_stages:
    runner.disable_stages = set(args.disable_stages)

if args.enable_tags:
    runner.enable_tags = set(args.enable_tags)

if args.disable_tags:
    runner.disable_tags = set(args.disable_tags)

if args.repeat:
    runner.repeat = args.repeat

# in no_action mode -> runner.enabled = False
runner.enabled = not args.no_action

runner.start()

if args.data:
    runner.add_data_file(args.data)
    runner.time2die.set(True)
elif args.server:
    runner.start_https_server()
else:
    logger.error('You need to set --data or --server option!')
    sys.exit(1)

try:
    processes_alive = True
    while processes_alive:
        processes_alive = False
        processes = multiprocessing.active_children()
        logger.debug("Active children: %s", processes)
        for process in processes:
            if not process.name.startswith("SyncManager"):
                processes_alive = True
        time.sleep(5)
except KeyboardInterrupt:
    print 'Got CTRL-C, exiting'
    for process in multiprocessing.active_children():
        process.terminate()
    sys.exit(1)

exit_status = runner.last_testing_exitstatus.get()

runner.manager.shutdown()

sys.exit(exit_status)
