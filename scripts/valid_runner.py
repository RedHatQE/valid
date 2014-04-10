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
import paramiko
import random
import string
import tempfile
import traceback
import BaseHTTPServer
import urlparse
import ssl
import re
import urllib2
import getpass
import subprocess
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


def strzero(value, maxvalue):
    """
    Generate string from number with leading zeros to save lexicographical order

    @param value: value to represent as string
    @type value: int

    @param maxvalue: maximum allowed value
    @type maxvalue: int

    @return: string with leading zeros
    @rtype: str
    """
    result = str(value)
    while len(result) < len(str(maxvalue)):
        result = '0' + result
    return result


def get_test_stages(params):
    """
    Get list of testing stages

    @param params: list of testing parameters
    @type params: list

    @return: list of all testing stages (e.g. [01stage1testcase01_xx_test,
             01stage1testcase02_xx_test, ...])
    @rtype: list
    """
    logger = logging.getLogger('valid.runner')
    logger.debug('Getting enabled stages for %s', params['iname'])
    result = []
    for module_name in sys.modules.keys():
        if module_name.startswith('valid.testing_modules.testcase'):
            test_name = module_name.split('.')[2]
            while True:
                try:
                    testcase = getattr(sys.modules[module_name], test_name)()
                    if test_name in params['disable_tests']:
                        # Test is disabled, skipping
                        break
                    if params['enable_tests'] and not test_name in params['enable_tests']:
                        # Test is not enabled, skipping
                        break
                    if not params['enable_tests']:
                        tags = set(testcase.tags)
                        if len(tags.intersection(params['disable_tags'])) != 0:
                            # Test disabled as it contains disabled tags
                            break
                        if params['enable_tags'] and len(tags.intersection(params['enable_tags'])) == 0:
                            # Test disabled as it doesn't contain enabled tags
                            break
                    applicable_flag = True
                    if hasattr(testcase, 'not_applicable'):
                        logger.debug('Checking not_applicable list for ' + test_name)
                        not_applicable = testcase.not_applicable
                        applicable_flag = False
                        for nakey in not_applicable.keys():
                            logger.debug('not_applicable key %s %s ... ', nakey, not_applicable[nakey])
                            rexp = re.compile(not_applicable[nakey])
                            if rexp.match(params[nakey]) is None:
                                applicable_flag = True
                                logger.debug('not_applicable check failed for ' + test_name + ' %s = %s', nakey, params[nakey])
                            else:
                                logger.debug('got not_applicable for ' + test_name + ' %s = %s' % (nakey, params[nakey]))
                    if hasattr(testcase, 'applicable'):
                        logger.debug('Checking applicable list for ' + test_name)
                        applicable = testcase.applicable
                        for akey in applicable.keys():
                            logger.debug('applicable key %s %s ... ', akey, applicable[akey])
                            rexp = re.compile(applicable[akey])
                            if not rexp.match(params[akey]):
                                logger.debug('Got \'not applicable\' for ' + test_name + ' %s = %s', akey, params[akey])
                                applicable_flag = False
                                break
                    if not applicable_flag:
                        break
                    for stage in testcase.stages:
                        if stage in params['disable_stages']:
                            # Stage is disabled
                            continue
                        if params['enable_stages'] and not stage in params['enable_stages']:
                            # Stage is not enabled
                            continue
                        # Everything is fine, appending stage to the result
                        result.append(stage + ':' + test_name)
                except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), err:
                    logger.error('bad test, %s %s', module_name, err)
                    logger.debug(traceback.format_exc())
                    sys.exit(1)
                break
    result.sort()
    if params['repeat'] > 1:
        # need to repeat whole test procedure N times
        result_repeat = []
        for cnt in range(1, params['repeat'] + 1):
            for stage in result:
                result_repeat.append(strzero(cnt, params['repeat']) + stage)
        result = result_repeat
    logger.debug('Testing stages %s discovered for %s', result, params['iname'])
    return result


def add_data(data, emails=None, subject=None):
    """
    Add testing data
    @param data: list of data fields
    @type params: list

    @param emails: comma-separated list of emails interested in result
    @type emails: str

    @param subject: email subject
    @type subject: str

    @return: transaction id or None
    @rtype: str or None
    """
    transaction_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
    logger = logging.getLogger('valid.runner')
    logger.info('Adding validation transaction ' + transaction_id)
    transaction_dict = {}
    count = 0
    for params in data:
        mandatory_fields = ['product', 'arch', 'region', 'version', 'ami']
        minimal_set = set(mandatory_fields)
        exact_set = set(params.keys())
        if minimal_set.issubset(exact_set):
            # we have all required keys
            for field in mandatory_fields:
                if type(params[field]) != str:
                    params[field] = str(params[field])
            if params['ami'] in transaction_dict.keys():
                logger.error('Ami %s was already added for transaction %s!', params['ami'], transaction_id)
                continue
            logger.debug('Got valid data line ' + str(params))
            hwp_found = False
            for hwpdir in ['hwp', '/usr/share/valid/hwp']:
                try:
                    hwpfd = open(hwpdir + '/' + params['arch'] + '.yaml', 'r')
                    hwp = yaml.load(hwpfd)
                    hwpfd.close()
                    # filter hwps based on args
                    hwp = [x for x in hwp if re.match(args.hwp_filter, x['ec2name']) is not None]
                    if not len(hwp):
                        # precautions
                        logger.info('no hwp match for %s; nothing to do', args.hwp_filter)
                        continue

                    logger.info('using hwps: %s',
                                 reduce(lambda x, y: x + ', %s' % str(y['ec2name']),
                                        hwp[1:],
                                        str(hwp[0]['ec2name'])
                                        )
                                 )
                    ninstances = 0
                    for hwp_item in hwp:
                        params_copy = params.copy()
                        params_copy.update(hwp_item)
                        if not 'bmap' in params_copy.keys():
                            params_copy['bmap'] = [{'name': '/dev/sda1', 'size': '15', 'delete_on_termination': True}]
                        if not 'userdata' in params_copy.keys():
                            params_copy['userdata'] = None
                        if not 'itype' in params_copy.keys():
                            params_copy['itype'] = 'hourly'

                        if not 'enable_stages' in params_copy:
                            params_copy['enable_stages'] = enable_stages
                        if not 'disable_stages' in params_copy:
                            params_copy['disable_stages'] = disable_stages
                        if not 'enable_tags' in params_copy:
                            params_copy['enable_tags'] = enable_tags
                        if not 'disable_tags' in params_copy:
                            params_copy['disable_tags'] = disable_tags
                        if not 'enable_tests' in params_copy:
                            params_copy['enable_tests'] = enable_tests
                        if not 'disable_tests' in params_copy:
                            params_copy['disable_tests'] = disable_tests

                        if not 'repeat' in params_copy:
                            params_copy['repeat'] = repeat

                        if not 'name' in params_copy:
                            params_copy['name'] = params_copy['ami'] + ' validation'

                        params_copy['transaction_id'] = transaction_id
                        params_copy['iname'] = 'Instance' + str(count) + '_' + transaction_id
                        params_copy['stages'] = get_test_stages(params_copy)
                        ninstances += len(params_copy['stages'])
                        if params_copy['stages'] != []:
                            logger.info('Adding ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                            mainq.put((0, 'create', params_copy))
                            count += 1
                        else:
                            logger.info('No tests for ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                    if ninstances > 0:
                        transaction_dict[params['ami']] = {'ninstances': ninstances, 'instances': []}
                        if emails:
                            transaction_dict[params['ami']]['emails'] = emails
                            if subject:
                                transaction_dict[params['ami']]['subject'] = subject
                    hwp_found = True
                    break
                except:
                    logger.debug(':' + traceback.format_exc())
            if not hwp_found:
                logger.error('HWP for ' + params['arch'] + ' is not found, skipping dataline for ' + params['ami'])
        else:
            # we something is missing
            logger.error('Got invalid data line: ' + str(params))
    if count > 0:
        resultdic[transaction_id] = transaction_dict
        logger.info('Validation transaction ' + transaction_id + ' added')
        return transaction_id
    else:
        logger.error('No data added')
        return None


class ServerProcess(multiprocessing.Process):
    """
    Process for handling HTTPS requests
    """
    def __init__(self, resultdic, resultdic_yaml, hname='0.0.0.0', port=8080):
        """
        Create ServerProcess object

        @param hostname: bind address
        @type hostname: str

        @param port: bind port
        @type port: int
        """
        self.hostname = hname
        self.port = port
        multiprocessing.Process.__init__(self, name='ServerProcess', target=self.runner, args=(resultdic, resultdic_yaml))

    def runner(self, resultdic, resultdic_yaml):
        """
        Run process
        """
        server_class = ValidHTTPServer
        httpd = server_class((self.hostname, self.port), HTTPHandler, resultdic, resultdic_yaml)
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       certfile=yamlconfig['server_ssl_cert'],
                                       keyfile=yamlconfig['server_ssl_key'],
                                       server_side=True,
                                       cert_reqs=ssl.CERT_REQUIRED,
                                       ca_certs=yamlconfig['server_ssl_ca'])
        httpd.serve_forever()


class ValidHTTPServer(BaseHTTPServer.HTTPServer):
    """ Valid HTTPS server """

    def __init__(self, server_address, RequestHandlerClass, resultdic, resultdic_yaml):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.resultdic = resultdic
        self.resultdic_yaml = resultdic_yaml


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    HTTP Handler
    """
    def __init__(self):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self)
        self.logger = logging.getLogger('valid.runner')

    def do_HEAD(self):
        """
        Process HEAD request
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """
        Process GET request
        """
        try:
            path = urlparse.urlparse(self.path).path
            query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
            self.logger.debug('GET request: ' + self.path)
            if path[-1:] == '/':
                path = path[:-1]
            if path == '':
                # info page
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><head><title>Validation status page</title></head>')
                self.wfile.write('<body>')
                self.wfile.write('<h1>Worker\'s queue</h1>')
                for q_item in mainq.queue:
                    self.wfile.write('<p>%s</p>' % str(q_item))
                self.wfile.write('<h1>Ongoing testing</h1>')
                for transaction_id in self.server.resultdic.keys():
                    self.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                    for ami in self.server.resultdic[transaction_id].keys():
                        self.wfile.write('<h3>Ami %s </h3>' % ami)
                        self.wfile.write('<p>%s</p>' % str(self.server.resultdic[transaction_id][ami]))
                self.wfile.write('<h1>Finished testing</h1>')
                for transaction_id in self.server.resultdic_yaml.keys():
                    self.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                self.wfile.write('</body></html>')
            elif path == '/result':
                # transaction result in yaml
                if not 'transaction_id' in query.keys():
                    raise Exception('transaction_id parameter is not set')
                transaction_id = query['transaction_id'][0]
                if transaction_id in self.server.resultdic_yaml.keys():
                    self.send_response(200)
                    self.send_header('Content-type', 'text/yaml')
                    self.end_headers()
                    self.wfile.write(self.server.resultdic_yaml[transaction_id])
                else:
                    if transaction_id in self.server.resultdic.keys():
                        self.send_response(200)
                        self.send_header('Content-type', 'text/yaml')
                        self.end_headers()
                        self.wfile.write(yaml.safe_dump({'result': 'In progress'}))
                    else:
                        raise Exception('No such transaction')
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><body>Bad url</body></html>')
        except Exception, err:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(err.message)
            self.logger.debug('HTTP Server:' + traceback.format_exc())

    def do_POST(self):
        """
        Process POST request
        """
        # Extract and print the contents of the POST
        length = int(self.headers['Content-Length'])
        try:
            post_data = urlparse.parse_qs(self.rfile.read(length).decode('utf-8'))
            if post_data and ('data' in post_data.keys()):
                data = yaml.load(post_data['data'][0])
                self.logger.debug('POST DATA:' + str(data))
                if 'emails' in post_data.keys():
                    emails = post_data['emails'][0]
                    self.logger.debug('POST EMAILS:' + emails)
                else:
                    emails = None
                if 'subject' in post_data.keys() and emails:
                    subject = post_data['subject'][0]
                    self.logger.debug('POST SUBJECT:' + subject)
                else:
                    subject = None
                transaction_id = add_data(data, emails, subject)
                if not transaction_id:
                    raise Exception('Bad data')
                self.send_response(200)
                self.send_header('Content-type', 'text/yaml')
                self.end_headers()
                self.wfile.write(yaml.safe_dump({'transaction_id': transaction_id}))
            else:
                raise Exception('Bad data')
        except Exception, err:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(err.message)


class WatchmanProcess(multiprocessing.Process):
    """
    Special Process to watch over other Processes:
    - Create WorkerProcesses when we have long queue
    - report result for a transaction when it's ready
    """
    def __init__(self, resultdic, resultdic_lock, resultdic_yaml):
        """
        Create WatchmanProcess object
        """
        multiprocessing.Process.__init__(self, name='WatchmanProcess', target=self.runner, args=(resultdic, resultdic_lock, resultdic_yaml))
        self.logger = logging.getLogger('valid.runner')

    def runner(self, resultdic, resultdic_lock, resultdic_yaml):
        """
        Run process
        """
        while True:
            self.logger.debug('WatchmanProcess: heartbeat numprocesses: %i', numprocesses.value)
            time.sleep(random.randint(2, 10))
            self.report_results(resultdic, resultdic_lock, resultdic_yaml)
            self.add_worker_processes(resultdic, resultdic_lock)
            if resultdic.keys() == [] and not httpserver:
                break

    def add_worker_processes(self, resultdic, resultdic_lock):
        """
        Create additional worker processes when something has to be done
        """
        processes_2create = min(maxprocesses - numprocesses.value, mainq.qsize())
        if processes_2create > 0:
            self.logger.debug('WatchmanProcess: should create %i additional worker processes', processes_2create)
            for _ in range(processes_2create):
                workprocess = valid.valid_worker.WorkerProcess(resultdic, resultdic_lock, mainq, numprocesses, minprocesses, yamlconfig, settlewait, maxtries, maxwait, httpserver)
                numprocesses.value += 1
                workprocess.start()

    def report_results(self, resultdic, resultdic_lock, resultdic_yaml):
        """
        Looking if we can report some transactions
        """
        with resultdic_lock:
            for transaction_id in resultdic.keys():
                # Checking all transactions
                transaction_dict = resultdic[transaction_id].copy()
                report_ready = True
                for ami in transaction_dict.keys():
                    # Checking all amis: they should be finished
                    if transaction_dict[ami]['ninstances'] != len(transaction_dict[ami]['instances']):
                        # Still have some jobs running ...
                        self.logger.debug('WatchmanProcess: ' + transaction_id + ': ' + ami + ':  waiting for ' + str(transaction_dict[ami]['ninstances']) + ' results, got ' + str(len(transaction_dict[ami]['instances'])))
                        report_ready = False
                if report_ready:
                    resfile = resdir + '/' + transaction_id + '.yaml'
                    result = []
                    data = transaction_dict
                    emails = None
                    subject = None
                    for ami in data.keys():
                        result_item = {'ami': data[ami]['instances'][0]['ami'],
                                       'product': data[ami]['instances'][0]['product'],
                                       'version': data[ami]['instances'][0]['version'],
                                       'arch': data[ami]['instances'][0]['arch'],
                                       'region': data[ami]['instances'][0]['region'],
                                       'console_output': {},
                                       'result': {}}
                        for instance in data[ami]['instances']:
                            if not instance['instance_type'] in result_item['result'].keys():
                                result_item['result'][instance['instance_type']] = instance['result'].copy()
                            else:
                                result_item['result'][instance['instance_type']].update(instance['result'])
                            # we're interested in latest console output only, overwriting
                            result_item['console_output'][instance['instance_type']] = instance['console_output']
                        result.append(result_item)
                        if 'emails' in data[ami].keys():
                            emails = data[ami]['emails']
                        if 'subject' in data[ami].keys():
                            subject = data[ami]['subject']
                    result_yaml = yaml.safe_dump(result)
                    resultdic_yaml[transaction_id] = result_yaml
                    try:
                        result_fd = open(resfile, 'w')
                        result_fd.write(result_yaml)
                        result_fd.close()
                        if emails:
                            for ami in result:
                                overall_result, bug_summary, bug_description = valid.valid_result.get_overall_result(ami)
                                msg = MIMEMultipart()
                                msg.preamble = 'Validation result'
                                if subject:
                                    msg['Subject'] = "[" + overall_result + "] " + subject
                                else:
                                    msg['Subject'] = "[" + overall_result + "] " + bug_summary
                                msg['From'] = mailfrom
                                msg['To'] = emails
                                txt = MIMEText(bug_description + '\n')
                                msg.attach(txt)
                                txt = MIMEText(yaml.safe_dump(ami), 'yaml')
                                msg.attach(txt)
                                smtp = smtplib.SMTP('localhost')
                                smtp.sendmail(mailfrom, emails.split(','), msg.as_string())
                                smtp.quit()
                    except Exception, err:
                        self.logger.error('WatchmanProcess: saving result failed, %s', err)
                    self.logger.info('Transaction ' + transaction_id + ' finished. Result: ' + resfile)
                    resultdic.pop(transaction_id)



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
maxtries = args.maxtries
maxwait = args.maxwait
settlewait = args.settlewait

minprocesses = args.minprocesses
maxprocesses = args.maxprocesses

httpserver = args.server

confd = open(args.config, 'r')
yamlconfig = yaml.load(confd)
confd.close()

if args.results_dir:
    resdir = args.results_dir
elif 'results_dir' in yamlconfig.keys():
    resdir = yamlconfig['results_dir']
else:
    resdir = '.'

# Check if result directory is writable
try:
    fd = open(resdir + '/.valid.tmp', 'w')
    fd.write('temp')
    fd.close()
    os.unlink(resdir + '/.valid.tmp')
except IOError, err:
    sys.stderr.write('Failed to create file in ' + resdir + ' %s ' % err + '\n')
    sys.exit(1)

if httpserver:
    for key in 'server_ssl_ca', 'server_ssl_cert', 'server_ssl_key':
        if not key in yamlconfig.keys():
            sys.stderr.write('You should specify ' + key + ' in ' + args.config + ' to run in server mode!\n')
            sys.exit(1)
        elif not os.path.exists(yamlconfig[key]):
            sys.stderr.write(key + 'file does not exist but required for server mode. Use valid_cert_creator.py to create it.\n')
            sys.exit(1)

if args.enable_tests:
    enable_tests = set(args.enable_tests)
else:
    enable_tests = None

if args.disable_tests:
    disable_tests = set(args.disable_tests)
else:
    disable_tests = set()

if args.enable_stages:
    enable_stages = set(args.enable_stages)
else:
    enable_stages = None

if args.disable_stages:
    disable_stages = set(args.disable_stages)
else:
    disable_stages = set()

if args.enable_tags:
    enable_tags = set(args.enable_tags)
else:
    enable_tags = None

if args.disable_tags:
    disable_tags = set(args.disable_tags)
else:
    disable_tags = set()

repeat = args.repeat

logger = logging.getLogger('valid.runner')

if args.debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logging.getLogger('valid.runner').setLevel(loglevel)
logging.getLogger('valid.testcase').setLevel(loglevel)

if not httpserver:
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
except re.error as err:
    print 'error compiling hwp-filter: %s: %s' % (args.hwp_filter, err)
    sys.exit(1)

logger.debug('Tags enabled: %s', enable_tags)
logger.debug('Tags disabled: %s', disable_tags)
logger.debug('Stages enabled: %s', enable_stages)
logger.debug('Stages disabled: %s', disable_stages)
logger.debug('Tests enabled: %s', enable_tests)
logger.debug('Tests disabled: %s', disable_tests)

mailfrom = 'root@localhost'
if httpserver:
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
    mailfrom = getpass.getuser() + '@' + hostname
    logger.debug('Will send resulting emails from ' + mailfrom)

logging.getLogger('boto').setLevel(logging.CRITICAL)

# Shared state
manager = multiprocessing.Manager()
# main queue for worker processes
mainq = manager.Queue()

# resulting dictionary
resultdic_lock = multiprocessing.Lock()
resultdic = manager.dict()

# resulting dictionary
resultdic_yaml = manager.dict()

# number of running processes
numprocesses = multiprocessing.Value('i', lock=True)
numprocesses.value = 0

if args.data:
    # Data file was supplied
    try:
        datafd = open(args.data, 'r')
        data2add = yaml.load(datafd)
        datafd.close()
    except Exception, err:
        logger.error('Failed to read data file %s with error %s', args.data, err)
        sys.exit(1)
    add_data(data2add)
elif not httpserver:
    logger.error('You need to set --data or --server option!')
    sys.exit(1)

for _ in range(minprocesses):
    # Creating minimum amount of worker processes
    wprocess = valid.valid_worker.WorkerProcess(resultdic, resultdic_lock, mainq, numprocesses, minprocesses, yamlconfig, settlewait, maxtries, maxwait, httpserver)
    numprocesses.value += 1
    wprocess.start()

watchprocess = WatchmanProcess(resultdic, resultdic_lock, resultdic_yaml)
watchprocess.start()

if httpserver:
    # Starting ServerProcess
    sprocess = ServerProcess(resultdic, resultdic_yaml)
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
