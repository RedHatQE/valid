#! /usr/bin/python -tt
"""
Validation runner
"""

import multiprocessing
import time
import logging
import argparse
import yaml
import os
import sys
import re
import urllib2
import getpass
import subprocess

sys.path.append("..")
sys.path.append(".")
import valid

def csv(value):
    """
    Generate list from comma-separated value

    @param value: comma-separated value
    @type value: string

    @return: list of values
    @rtype: list of str
    """
    return map(str, value.split(','))


class SharedData(object):
    def __init__(self):
        self.resultdic = None
        self.resultdic_lock = None
        self.resultdic_yaml = None
        self.mainq = None
        self.mailfrom = None
        self.numprocesses = None
        self.minprocesses = None
        self.maxprocesses = None
        self.yamlconfig = None
        self.settlewait = None
        self.maxtries = None
        self.maxwait = None
        self.httpserver = None
        self.resdir = None
        self.disable_stages = None
        self.enable_stages = None
        self.disable_tags = None
        self.enable_tags = None
        self.disable_tests = None
        self.enable_tests = None
        self.repeat = None
        self.hname = '0.0.0.0'
        self.port = 8080
        self.hwp_filter = None
        self.emails = None
        self.subject = None
        self.mailfrom = None

shareddata = SharedData()

# pylint: disable=C0103,E1101
argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--data', help='data file for validation')
argparser.add_argument('--config',
                       default='/etc/validation.yaml', help='use supplied yaml config file')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')

argparser.add_argument('--disable-stages', type=csv, help='disable specified stages')
argparser.add_argument('--enable-stages', type=csv, help='enable specified stages (overrides --disable-stages)')

argparser.add_argument('--disable-tests', type=csv, help='disable specified tests')
argparser.add_argument('--enable-tests', type=csv, help='enable specified tests only (overrides --disabe-tests)')

argparser.add_argument('--disable-tags', type=csv, help='disable specified tags')
argparser.add_argument('--enable-tags', type=csv, help='enable specified tags only (overrides --disabe-tags)',
                       default='default')

argparser.add_argument('--repeat', type=int, help='repeat testing with the same instance N times',
                       default=1)

argparser.add_argument('--maxtries', type=int,
                       default=30, help='maximum number of tries')
argparser.add_argument('--maxwait', type=int,
                       default=900, help='maximum wait time for instance creation')

argparser.add_argument('--minprocesses', type=int,
                       default=8, help='minimum number of worker processes')
argparser.add_argument('--maxprocesses', type=int,
                       default=32, help='maximum number of worker processes')

argparser.add_argument('--results-dir',
                       default=False, help='put resulting yaml files to specified location')
argparser.add_argument('--server', action='store_const', const=True,
                       default=False, help='run HTTP server')
argparser.add_argument('--settlewait', type=int,
                       default=30, help='wait for instance to settle before testing')
argparser.add_argument('--hwp-filter', help='select hwps to instantiate',
                       default='.*')

args = argparser.parse_args()
shareddata.maxtries = args.maxtries
shareddata.maxwait = args.maxwait
shareddata.settlewait = args.settlewait

shareddata.minprocesses = args.minprocesses
shareddata.maxprocesses = args.maxprocesses

shareddata.httpserver = args.server

confd = open(args.config, 'r')
shareddata.yamlconfig = yaml.load(confd)
confd.close()

if args.results_dir:
    shareddata.resdir = args.results_dir
elif 'results_dir' in shareddata.yamlconfig.keys():
    shareddata.resdir = shareddata.yamlconfig['results_dir']
else:
    shareddata.resdir = '.'

# Check if result directory is writable
try:
    fd = open(shareddata.resdir + '/.valid.tmp', 'w')
    fd.write('temp')
    fd.close()
    os.unlink(shareddata.resdir + '/.valid.tmp')
except IOError, err:
    sys.stderr.write('Failed to create file in ' + shareddata.resdir + ' %s ' % err + '\n')
    sys.exit(1)

if shareddata.httpserver:
    for key in 'server_ssl_ca', 'server_ssl_cert', 'server_ssl_key':
        if not key in shareddata.yamlconfig.keys():
            sys.stderr.write('You should specify ' + key + ' in ' + args.config + ' to run in server mode!\n')
            sys.exit(1)
        elif not os.path.exists(shareddata.yamlconfig[key]):
            sys.stderr.write(key + 'file does not exist but required for server mode. Use valid_cert_creator.py to create it.\n')
            sys.exit(1)

if args.enable_tests:
    shareddata.enable_tests = set(args.enable_tests)

if args.disable_tests:
    shareddata.disable_tests = set(args.disable_tests)
else:
    shareddata.disable_tests = set()

if args.enable_stages:
    shareddata.enable_stages = set(args.enable_stages)

if args.disable_stages:
    shareddata.disable_stages = set(args.disable_stages)
else:
    shareddata.disable_stages = set()

if args.enable_tags:
    shareddata.enable_tags = set(args.enable_tags)

if args.disable_tags:
    shareddata.disable_tags = set(args.disable_tags)
else:
    shareddata.disable_tags = set()

shareddata.repeat = args.repeat

logger = logging.getLogger('valid.runner')

if args.debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logging.getLogger('valid.runner').setLevel(loglevel)
logging.getLogger('valid.testcase').setLevel(loglevel)

if not shareddata.httpserver:
    logging.basicConfig(level=loglevel, format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
else:
    # We use systemd-journald, skip date-time
    if args.debug:
        logging.basicConfig(level=loglevel, format='%(levelname)s %(message)s')
    else:
        # skip loglevel as well
        logging.basicConfig(level=loglevel, format='%(message)s')

if args.debug:
    logging.getLogger('paramiko').setLevel(logging.DEBUG)
else:
    logging.getLogger('paramiko').setLevel(logging.ERROR)

try:
    re.compile(args.hwp_filter)
    shareddata.hwp_filter = args.hwp_filter
except re.error as err:
    print 'error compiling hwp-filter: %s: %s' % (args.hwp_filter, err)
    sys.exit(1)

logger.debug('Tags enabled: %s', shareddata.enable_tags)
logger.debug('Tags disabled: %s', shareddata.disable_tags)
logger.debug('Stages enabled: %s', shareddata.enable_stages)
logger.debug('Stages disabled: %s', shareddata.disable_stages)
logger.debug('Tests enabled: %s', shareddata.enable_tests)
logger.debug('Tests disabled: %s', shareddata.disable_tests)

shareddata.mailfrom = 'root@localhost'
if shareddata.httpserver:
    hostname = ''
    try:
        logger.debug('Trying to fetch real hostname from EC2')
        response = urllib2.urlopen('http://169.254.169.254/latest/meta-data/public-hostname', timeout=5)
        hostname = response.read()
        logger.debug('Fetched %s as real hostname')
    except:
        # looks like we're not in EC2 environment
        pass
    if not hostname or hostname == '':
        hostname = subprocess.check_output(['hostname', '-f'])[:-1]
    shareddata.mailfrom = getpass.getuser() + '@' + hostname
    logger.debug('Will send resulting emails from ' + shareddata.mailfrom)

logging.getLogger('boto').setLevel(logging.CRITICAL)

# Shared state
manager = multiprocessing.Manager()
# main queue for worker processes
shareddata.mainq = manager.Queue()

# resulting dictionary
shareddata.resultdic_lock = multiprocessing.Lock()
shareddata.resultdic = manager.dict()

# resulting dictionary
shareddata.resultdic_yaml = manager.dict()

# number of running processes
shareddata.numprocesses = multiprocessing.Value('i', lock=True)
shareddata.numprocesses.value = 0

if args.data:
    # Data file was supplied
    try:
        datafd = open(args.data, 'r')
        data2add = yaml.load(datafd)
        datafd.close()
    except Exception, err:
        logger.error('Failed to read data file %s with error %s', args.data, err)
        sys.exit(1)
    valid.valid_misc.add_data(shareddata, data2add)
elif not shareddata.httpserver:
    logger.error('You need to set --data or --server option!')
    sys.exit(1)

for _ in range(shareddata.minprocesses):
    # Creating minimum amount of worker processes
    wprocess = valid.valid_worker.WorkerProcess(shareddata)
    shareddata.numprocesses.value += 1
    wprocess.start()

watchprocess = valid.valid_watchman.WatchmanProcess(shareddata)
watchprocess.start()

if shareddata.httpserver:
    # Starting ServerProcess
    sprocess = valid.valid_server.ServerProcess(shareddata)
    sprocess.start()

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
manager.shutdown()
