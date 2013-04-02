#! /usr/bin/python -tt

import Queue
import threading
import boto
import time
import logging
import argparse
import yaml
import os
import sys
import sets
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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from patchwork.connection import Connection
from patchwork.expect import *
from boto import ec2
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

import valid
from valid import valid_result


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
    logging.debug('Getting enabled stages for %s' % params['iname'])
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
                        logging.debug('Checking not_applicable list for ' + test_name)
                        not_applicable = testcase.not_applicable
                        for key in not_applicable.keys():
                            logging.debug('not_applicable key %s %s ... ' % (key, not_applicable[key]))
                            r = re.compile(not_applicable[key])
                            if r.match(params[key]):
                                logging.debug('got not_applicable for ' + test_name + ' %s = %s' % (key, params[key]))
                                applicable_flag = False
                                break
                    if hasattr(testcase, 'applicable'):
                        logging.debug('Checking applicable list for ' + test_name)
                        applicable = testcase.applicable
                        for key in applicable.keys():
                            logging.debug('applicable key %s %s ... ' % (key, applicable[key]))
                            r = re.compile(applicable[key])
                            if not r.match(params[key]):
                                logging.debug('Got \'not applicable\' for ' + test_name + ' %s = %s' % (key, params[key]))
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
                except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), e:
                    logging.error('bad test, %s %s' % (module_name, e))
                    logging.debug(traceback.format_exc())
                    sys.exit(1)
                break
    result.sort()
    if params['repeat'] > 1:
        # need to repeat whole test procedure N times
        result_repeat = []
        for i in range(1, params['repeat'] + 1):
            for stage in result:
                result_repeat.append(strzero(i, params['repeat']) + stage)
        result = result_repeat
    logging.debug('Testing stages %s discovered for %s' % (result, params['iname']))
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
    with resultdic_lock:
        transaction_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        logging.info('Adding validation transaction ' + transaction_id)
        resultdic[transaction_id] = {}
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
                if params['ami'] in resultdic[transaction_id].keys():
                    logging.error('Ami %s was already added for transaction %s!' % (params['ami'], transaction_id))
                    continue
                logging.debug('Got valid data line ' + str(params))
                hwp_found = False
                for hwpdir in ['hwp', '/usr/share/valid/hwp']:
                    try:
                        hwpfd = open(hwpdir + '/' + params['arch'] + '.yaml', 'r')
                        hwp = yaml.load(hwpfd)
                        hwpfd.close()
                        # filter hwps based on args
                        hwp = filter(lambda x: re.match(args.hwp_filter,
                                    x['ec2name']), hwp)
                        if not len(hwp):
                            # precautions
                            logging.info('no hwp match for %s; nothing to do' %
                                        args.hwp_filter)
                            continue

                        logging.info('using hwps: %s' %
                            reduce(
                                lambda x, y: x + ', %s' % str(y['ec2name']),
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
                                logging.info('Adding ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                                mainq.put((0, 'create', params_copy))
                                count += 1
                            else:
                                logging.info('No tests for ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                        if ninstances > 0:
                            resultdic[transaction_id][params['ami']] = {'ninstances': ninstances, 'instances': []}
                            if emails:
                                resultdic[transaction_id][params['ami']]['emails'] = emails
                                if subject:
                                    resultdic[transaction_id][params['ami']]['subject'] = subject
                        hwp_found = True
                        break
                    except:
                        logging.debug(':' + traceback.format_exc())
                if not hwp_found:
                    logging.error('HWP for ' + params['arch'] + ' is not found, skipping dataline for ' + params['ami'])
            else:
                # we something is missing
                logging.error('Got invalid data line: ' + str(params))
        if count > 0:
            logging.info('Validation transaction ' + transaction_id + ' added')
            return transaction_id
        else:
            resultdic.pop(transaction_id)
            logging.info('No data added')
            return None


def remote_command(connection, command, timeout=5):
    """
    Execute a remote command via connection

    @param connection: Connection to the host
    @type connection: L{Connection}

    @param command: command to execute
    @type command: str

    @param timeout: timeout for performing expect operation
    @type  timeout: int

    @return: return value or None
    @rtype: int or None

    @raises ExpectFailed
    """
    status = connection.recv_exit_status(command + ' >/dev/null 2>&1', timeout)
    if status != 0:
        raise ExpectFailed('Command ' + command + ' failed with ' + str(status) + ' status.')
    return status


class ServerThread(threading.Thread):
    """
    Thread for handling HTTPS requests
    """
    def __init__(self, hostname='0.0.0.0', port=8080):
        """
        Create ServerThread object

        @param hostname: bind address
        @type hostname: str

        @param port: bind port
        @type port: int
        """
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.port = port

    def run(self):
        """
        Run Thread
        """
        server_class = BaseHTTPServer.HTTPServer
        httpd = server_class((self.hostname, self.port), HTTPHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       certfile=yamlconfig['server_ssl_cert'],
                                       keyfile=yamlconfig['server_ssl_key'],
                                       server_side=True,
                                       cert_reqs=ssl.CERT_REQUIRED,
                                       ca_certs=yamlconfig['server_ssl_ca'])
        httpd.serve_forever()


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    HTTP Handler
    """
    def do_HEAD(s):
        """
        Process HEAD request
        """
        s.send_response(200)
        s.send_header('Content-type', 'text/html')
        s.end_headers()

    def do_GET(s):
        """
        Process GET request
        """
        try:
            path = urlparse.urlparse(s.path).path
            query = urlparse.parse_qs(urlparse.urlparse(s.path).query)
            logging.debug('GET request: ' + s.path)
            if path[-1:] == '/':
                path = path[:-1]
            if path == '':
                # info page
                s.send_response(200)
                s.send_header('Content-type', 'text/html')
                s.end_headers()
                s.wfile.write('<html><head><title>Validation status page</title></head>')
                s.wfile.write('<body>')
                s.wfile.write('<h1>Worker\'s queue</h1>')
                for q_item in mainq.queue:
                    s.wfile.write('<p>%s</p>' % str(q_item))
                s.wfile.write('<h1>Ongoing testing</h1>')
                with resultdic_lock:
                    for transaction_id in resultdic.keys():
                        s.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                        for ami in resultdic[transaction_id].keys():
                            s.wfile.write('<h3>Ami %s </h3>' % ami)
                            s.wfile.write('<p>%s</p>' % str(resultdic[transaction_id][ami]))
                s.wfile.write('<h1>Finished testing</h1>')
                with resultdic_yaml_lock:
                    for transaction_id in resultdic_yaml.keys():
                        s.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                s.wfile.write('</body></html>')
            elif path == '/result':
                # transaction result in yaml
                if not 'transaction_id' in query.keys():
                    raise Exception('transaction_id parameter is not set')
                transaction_id = query['transaction_id'][0]
                with resultdic_yaml_lock:
                    if transaction_id in resultdic_yaml.keys():
                        s.send_response(200)
                        s.send_header('Content-type', 'text/yaml')
                        s.end_headers()
                        s.wfile.write(resultdic_yaml[transaction_id])
                    else:
                        with resultdic_lock:
                            if transaction_id in resultdic.keys():
                                s.send_response(200)
                                s.send_header('Content-type', 'text/yaml')
                                s.end_headers()
                                s.wfile.write(yaml.safe_dump({'result': 'In progress'}))
                            else:
                                raise Exception('No such transaction')
            else:
                s.send_response(404)
                s.send_header('Content-type', 'text/html')
                s.end_headers()
                s.wfile.write('<html><body>Bad url</body></html>')
        except Exception, e:
            s.send_response(400)
            s.send_header('Content-type', 'text/plain')
            s.end_headers()
            s.wfile.write(e.message)
            logging.debug('HTTP Server:' + traceback.format_exc())

    def do_POST(s):
        """
        Process POST request
        """
        # Extract and print the contents of the POST
        length = int(s.headers['Content-Length'])
        try:
            post_data = urlparse.parse_qs(s.rfile.read(length).decode('utf-8'))
            if post_data and ('data' in post_data.keys()):
                data = yaml.load(post_data['data'][0])
                logging.debug('POST DATA:' + str(data))
                if 'emails' in post_data.keys():
                    emails = post_data['emails'][0]
                    logging.debug('POST EMAILS:' + emails)
                else:
                    emails = None
                if 'subject' in post_data.keys() and emails:
                    subject = post_data['subject'][0]
                    logging.debug('POST SUBJECT:' + subject)
                else:
                    subject = None
                transaction_id = add_data(data, emails, subject)
                if not transaction_id:
                    raise Exception('Bad data')
                s.send_response(200)
                s.send_header('Content-type', 'text/yaml')
                s.end_headers()
                s.wfile.write(yaml.safe_dump({'transaction_id': transaction_id}))
            else:
                raise Exception('Bad data')
        except Exception, e:
                s.send_response(400)
                s.send_header('Content-type', 'text/plain')
                s.end_headers()
                s.wfile.write(e.message)


class WatchmanThread(threading.Thread):
    """
    Special Thread to watch over other Threads:
    - Create WorkerThreads when we have long queue
    - report result for a transaction when it's ready
    """

    def run(self):
        """
        Run Thread
        """
        while True:
            with numthreads_lock:
                logging.debug('WatchmanThread: heartbeat numthreads: %i' % numthreads)
            time.sleep(random.randint(2, 10))
            self.report_results()
            self.add_worker_threads()
            with resultdic_lock:
                if resultdic == {} and not httpserver:
                    break

    def add_worker_threads(self):
        """
        Create additional worker threads when something has to be done
        """
        global numthreads
        global numthreads_lock
        with numthreads_lock:
            threads_to_create = min(maxthreads - numthreads, mainq.qsize())
        if threads_to_create > 0:
            logging.debug('WatchmanThread: shoulkd create %i additional worker threads' % threads_to_create)
            for i in range(threads_to_create):
                wthread = WorkerThread()
                with numthreads_lock:
                    numthreads += 1
                wthread.start()

    def report_results(self):
        """
        Looking if we can report some transactions
        """
        with resultdic_lock:
            """ Dictionary is now locked """
            for transaction_id in resultdic.keys():
                """ Checking all transactions """
                report_ready = True
                for ami in resultdic[transaction_id].keys():
                    """ Checking all amis: they should be finished """
                    if resultdic[transaction_id][ami]['ninstances'] != len(resultdic[transaction_id][ami]['instances']):
                        """ Still have some jobs running ..."""
                        logging.debug('WatchmanThread: ' + transaction_id + ': ' + ami + ':  waiting for ' + str(resultdic[transaction_id][ami]['ninstances']) + ' results, got ' + str(len(resultdic[transaction_id][ami]['instances'])))
                        report_ready = False
                if report_ready:
                    resfile = resdir + '/' + transaction_id + '.yaml'
                    result = []
                    data = resultdic[transaction_id]
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
                    with resultdic_yaml_lock:
                        resultdic_yaml[transaction_id] = result_yaml
                    try:
                        result_fd = open(resfile, 'w')
                        result_fd.write(result_yaml)
                        result_fd.close()
                        if emails:
                            for ami in result:
                                overall_result, bug_summary, bug_description = valid_result.get_overall_result(ami)
                                msg = MIMEMultipart()
                                msg.preamble = 'Validation result'
                                if subject:
                                    msg['Subject'] = subject
                                else:
                                    msg['Subject'] = bug_summary
                                msg['From'] = mailfrom
                                msg['To'] = emails
                                txt = MIMEText(bug_description + '\n')
                                msg.attach(txt)
                                txt = MIMEText(yaml.safe_dump(ami), 'yaml')
                                msg.attach(txt)
                                s = smtplib.SMTP('localhost')
                                s.sendmail(mailfrom, emails.split(','), msg.as_string())
                                s.quit()
                    except Exception, e:
                        logging.error('WatchmanThread: saving result failed, %s' % e)
                    logging.info('Transaction ' + transaction_id + ' finished. Result: ' + resfile)
                    resultdic.pop(transaction_id)


class WorkerThread(threading.Thread):
    """
    Worker Thread to do actual testing
    """
    def __init__(self):
        """
        Create WorkerThread object
        """
        threading.Thread.__init__(self)

    def run(self):
        """
        Run thread:
        - Get tasks from mainq (create/setup/test/terminate)
        - Check for maxtries
        """
        global numthreads
        global numthreads_lock
        while True:
            with numthreads_lock:
                logging.debug(self.getName() + ': heartbeat numthreads: %i' % numthreads)
            with resultdic_lock:
                if resultdic == {} and not httpserver:
                    with numthreads_lock:
                        logging.debug(self.getName() + ': not in server mode and nothing to do, suiciding')
                        numthreads -= 1
                        break
                    break
            if mainq.empty():
                with numthreads_lock:
                    if numthreads > minthreads:
                        logging.debug(self.getName() + ': too many worker threads and nothing to do, suiciding')
                        numthreads -= 1
                        break
                time.sleep(random.randint(2, 10))
                continue
            try:
                (ntry, action, params) = mainq.get()
                mainq.task_done()
            except:
                continue
            if ntry > maxtries:
                # Maxtries reached: something is wrong, reporting 'failure' and terminating the instance
                logging.error(self.getName() + ': ' + action + ':' + str(params) + ' failed after ' + str(maxtries) + ' tries')
                if action in ['create', 'setup']:
                    params['result'] = {action: 'failure'}
                elif action == 'test':
                    params['result'] = {params['stages'][0]: 'failure'}
                if action != 'terminate':
                    # we need to change expected value in resultdic
                    with resultdic_lock:
                        resultdic[params['transaction_id']][params['ami']]['ninstances'] -= (len(params['stages']) - 1)
                    self.report_results(params)
                    if 'id' in params.keys():
                        # Try to terminate the instance
                        mainq.put((0, 'terminate', params.copy()))
                continue
            if action == 'create':
                # create an instance
                logging.debug(self.getName() + ': picking up ' + params['iname'])
                self.do_create(ntry, params)
            elif action == 'setup':
                # setup instance for testing
                logging.debug(self.getName() + ': doing setup for ' + params['iname'])
                res = self.do_setup(ntry, params)
            elif action == 'test':
                # do some testing
                logging.debug(self.getName() + ': doing testing for ' + params['iname'])
                res = self.do_testing(ntry, params)
            elif action == 'terminate':
                # terminate instance
                logging.debug(self.getName() + ': terminating ' + params['iname'])
                self.do_terminate(ntry, params)

    def report_results(self, params):
        """
        Report results

        @param params: list of testing parameters
        @type params: list
        """
        console_output = ''
        try:
            from pprint import pprint
            connection = params['instance']['connection']
            console_output = connection.get_console_output(params['id']).output
            logging.debug(self.getName() + ': got console output for %s: %s' % (params['iname'], console_output))
        except Exception, e:
            logging.error(self.getName() + ': report_results: Failed to get console output %s' % e)
        with resultdic_lock:
            report_value = {'instance_type': params['ec2name'],
                            'ami': params['ami'],
                            'region': params['region'],
                            'arch': params['arch'],
                            'version': params['version'],
                            'product': params['product'],
                            'console_output': console_output,
                            'result': params['result']}
            resultdic[params['transaction_id']][params['ami']]['instances'].append(report_value)

    def do_create(self, ntry, params):
        """
        Create stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        result = None
        logging.debug(self.getName() + ': trying to create instance  ' + params['iname'] + ', ntry ' + str(ntry))
        ntry += 1
        try:
            bmap = BlockDeviceMapping()
            for device in params['bmap']:
                if not 'name' in device.keys():
                    logging.debug(self.getName() + ': bad device ' + str(device))
                    continue
                d = BlockDeviceType()
                if 'size' in device.keys():
                    d.size = device['size']
                if 'delete_on_termination' in device.keys():
                    d.delete_on_termination = device['delete_on_termination']
                if 'ephemeral_name' in device.keys():
                    d.ephemeral_name = device['ephemeral_name']
                bmap[device['name']] = d

            reg = boto.ec2.get_region(params['region'], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            (ssh_key_name, ssh_key) = yamlconfig['ssh'][params['region']]
            # all handled params to be put in here
            boto_params = ['ami', 'subnet_id']
            for param in boto_params:
                params.setdefault(param)
            reservation = connection.run_instances(
                params['ami'],
                instance_type=params['ec2name'],
                key_name=ssh_key_name,
                block_device_map=bmap,
                subnet_id=params['subnet_id'],
                user_data=params['userdata']
            )
            myinstance = reservation.instances[0]
            count = 0
            # Sometimes EC2 failes to return something meaningful without small timeout between run_instances() and update()
            time.sleep(10)
            while myinstance.update() == 'pending' and count < maxwait / 5:
                # Waiting out instance to appear
                logging.debug(params['iname'] + '... waiting...' + str(count))
                time.sleep(5)
                count += 1
            connection.close()
            instance_state = myinstance.update()
            if instance_state == 'running':
                # Instance appeared - scheduling 'setup' stage
                myinstance.add_tag('Name', params['name'])
                result = myinstance.__dict__
                logging.info(self.getName() + ': created instance ' + params['iname'] + ', ' + result['id'] + ':' + result['public_dns_name'])
                # packing creation results into params
                params['id'] = result['id']
                params['instance'] = result.copy()
                mainq.put((0, 'setup', params))
                return
            elif instance_state == 'pending':
                # maxwait seconds is enough to create an instance. If not -- EC2 failed.
                logging.error('Error during instance creation: timeout in pending state')
                result = myinstance.__dict__
                if 'id' in result.keys():
                    # terminate stucked instance
                    params['id'] = result['id']
                    params['instance'] = result.copy()
                    mainq.put((0, 'terminate', params.copy()))
            else:
                # error occured
                logging.error('Error during instance creation: ' + instance_state)

        except boto.exception.EC2ResponseError, e:
            # Boto errors should be handled according to their error Message - there are some well-known ones
            logging.debug(self.getName() + ': got boto error during instance creation: %s' % e)
            if str(e).find('<Code>InstanceLimitExceeded</Code>') != -1:
                # InstanceLimit is temporary problem
                logging.debug(self.getName() + ': got InstanceLimitExceeded - not increasing ntry')
                ntry -= 1
            elif str(e).find('<Code>InvalidParameterValue</Code>') != -1:
                # InvalidParameterValue is really bad
                logging.error(self.getName() + ': got boto error during instance creation: %s' % e)
                # Try to speed up whole testing process, it's hardly possible to recover from this error
                ntry += args.maxtries // 2 + 1
            elif str(e).find('<Code>Unsupported</Code>') != -1:
                # Unsupported
                logging.error(self.getName() + ': got Unsupported - most likely the permanent error: %s' % e)
                ntry += args.maxtries // 2 + 1
            else:
                logging.debug(self.getName() + ':' + traceback.format_exc())
        except socket.error, e:
            # Network errors are usual, reschedult silently
            logging.debug(self.getName() + ': got socket error during instance creation: %s' % e)
            logging.debug(self.getName() + ':' + traceback.format_exc())
        except Exception, e:
            # Unexpected error happened
            logging.error(self.getName() + ': got error during instance creation: %s %s' % (type(e), e))
            logging.debug(self.getName() + ':' + traceback.format_exc())
        logging.debug(self.getName() + ': something went wrong with ' + params['iname'] + ' during creation, ntry: ' + str(ntry) + ', rescheduling')
        # reschedule creation
        time.sleep(10)
        mainq.put((ntry, 'create', params.copy()))

    def do_setup(self, ntry, params):
        """
        Setup stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        try:
            logging.debug(self.getName() + ': trying to do setup for ' + ', ntry ' + str(ntry))
            (ssh_key_name, ssh_key) = yamlconfig['ssh'][params['region']]
            logging.debug(self.getName() + ': ssh-key ' + ssh_key)

            for user in ['ec2-user', 'cloud-user']:
                # If we're able to login with one of these users allow root ssh immediately
                try:
                    con = Connection(params['instance'], user, ssh_key)
                    Expect.ping_pong(con, 'uname', 'Linux')
                    Expect.ping_pong(con, 'su -c \'cp -af /home/' + user + '/.ssh/authorized_keys /root/.ssh/authorized_keys; chown root.root /root/.ssh/authorized_keys; restorecon /root/.ssh/authorized_keys\' && echo SUCCESS', '\r\nSUCCESS\r\n')
                except:
                    pass

            con = Connection(params['instance'], 'root', ssh_key)
            remote_command(con, '[ `uname` = \'Linux\' ]')
            logging.debug(self.getName() + ': sleeping for ' + str(settlewait) + ' sec. to make sure instance has been settled.')
            time.sleep(settlewait)

            setup_scripts = []
            if 'setup' in yamlconfig:
                # upload and execute a setup script as root in /tmp/
                logging.debug(self.getName() + ': executing global setup script: %s' % yamlconfig['setup'])
                local_script_path = os.path.expandvars(os.path.expanduser(yamlconfig['setup']))
                setup_scripts.append(local_script_path)
            tf = tempfile.NamedTemporaryFile(delete=False)
            if 'setup' in params.keys() and params['setup']:
                if type(params['setup']) is list:
                    params['setup'] = '\n'.join(map(lambda x: str(x), params['setup']))
                logging.debug(self.getName() + ': executing ami-specific setup script: %s' % params['setup'])
                tf.write(params['setup'])
                setup_scripts.append(tf.name)
            tf.close()
            for script in setup_scripts:
                remote_script_path = '/tmp/' + os.path.basename(script)
                con.sftp.put(script, remote_script_path)
                con.sftp.chmod(remote_script_path, 0700)
                remote_command(con, remote_script_path)
            os.unlink(tf.name)
            con.disconnect()
            mainq.put((0, 'test', params.copy()))
        except (socket.error, paramiko.SFTPError, paramiko.SSHException, paramiko.PasswordRequiredException, paramiko.AuthenticationException, ExpectFailed) as e:
            logging.debug(self.getName() + ': got \'predictable\' error during instance setup, %s, ntry: %i' % (e, ntry))
            logging.debug(self.getName() + ':' + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, 'setup', params.copy()))
        except Exception, e:
            logging.error(self.getName() + ': got error during instance setup, %s %s, ntry: %i' % (type(e), e, ntry))
            logging.debug(self.getName() + ':' + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, 'setup', params.copy()))

    def do_testing(self, ntry, params):
        """
        Testing stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        try:
            stage = params['stages'][0]
            logging.debug(self.getName() + ': trying to do testing for ' + params['iname'] + ' ' + stage + ', ntry ' + str(ntry))

            (ssh_key_name, ssh_key) = yamlconfig['ssh'][params['region']]
            logging.debug(self.getName() + ': ssh-key ' + ssh_key)

            con = Connection(params['instance'], 'root', ssh_key)
            Expect.ping_pong(con, 'uname', 'Linux')

            logging.info(self.getName() + ': doing testing for ' + params['iname'] + ' ' + stage)

            try:
                test_name = stage.split(':')[1]
                testcase = getattr(sys.modules['valid.testing_modules.' + test_name], test_name)()
                logging.debug(self.getName() + ': doing test ' + test_name + ' for ' + params['iname'] + ' ' + stage)
                test_result = testcase.test(con, params)
                logging.debug(self.getName() + ': ' + params['iname'] + ': test ' + test_name + ' finised with ' + str(test_result))
                result = test_result
            except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError, boto.exception.EC2ResponseError), e:
                logging.error(self.getName() + ': bad test, %s %s' % (stage, e))
                logging.debug(self.getName() + ':' + traceback.format_exc())
                result = 'Failure'

            logging.info(self.getName() + ': done testing for ' + params['iname'] + ' ' + stage)

            params_new = params.copy()
            if len(params['stages']) > 1:
                params_new['stages'] = params['stages'][1:]
                mainq.put((0, 'test', params_new))
            else:
                mainq.put((0, 'terminate', params_new))
            logging.debug(self.getName() + ': done testing for ' + params['iname'] + ', result: ' + str(result))
            params['result'] = {params['stages'][0]: result}
            con.disconnect()
            self.report_results(params)
        except (socket.error, paramiko.SFTPError, paramiko.SSHException, paramiko.PasswordRequiredException, paramiko.AuthenticationException, ExpectFailed) as e:
            # Looks like we've failed to connect to the instance
            logging.debug(self.getName() + ': got \'predictable\' error during instance testing, %s, ntry: %i' % (e, ntry))
            logging.debug(self.getName() + ':' + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, 'test', params.copy()))
        except Exception, e:
            # Got unexpected error
            logging.error(self.getName() + ': got error during instance testing, %s %s, ntry: %i' % (type(e), e, ntry))
            logging.debug(self.getName() + ':' + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, 'test', params.copy()))

    def do_terminate(self, ntry, params):
        """
        Terminate stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        try:
            logging.debug(self.getName() + ': trying to terminata instance  ' + params['iname'] + ', ntry ' + str(ntry))
            connection = params['instance']['connection']
            res = connection.terminate_instances([params['id']])
            logging.info(self.getName() + ': terminated ' + params['iname'])
            connection.close()
            return res
        except Exception, e:
            logging.error(self.getName() + ': got error during instance termination, %s %s' % (type(e), e))
            logging.debug(self.getName() + ':' + traceback.format_exc())
            mainq.put((ntry + 1, 'terminate', params.copy()))

argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--data', help='data file for validation')
argparser.add_argument('--config',
                       default='/etc/validation.yaml', help='use supplied yaml config file')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')

argparser.add_argument('--disable-stages', type=csv, help='disable specified stages')
argparser.add_argument('--enable-stages', type=csv, help='enable specified stages (overrides --disable-stages')

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

argparser.add_argument('--minthreads', type=int,
                       default=10, help='minimum number of worker threads')
argparser.add_argument('--maxthreads', type=int,
                       default=100, help='maximum number of worker threads')

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

minthreads = args.minthreads
maxthreads = args.maxthreads

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
except IOError, e:
    sys.stderr.write('Failed to create file in ' + resdir + ' %s ' % e + '\n')
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

ec2_key = yamlconfig['ec2']['ec2-key']
ec2_secret_key = yamlconfig['ec2']['ec2-secret-key']

if args.debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

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
except re.error as e:
    print 'error compiling hwp-filter: %s: %s' % (args.hwp_filter, e)
    sys.exit(1)

logging.debug('Tags enabled: %s' % enable_tags)
logging.debug('Tags disabled: %s' % disable_tags)
logging.debug('Stages enabled: %s' % enable_stages)
logging.debug('Stages disabled: %s' % disable_stages)
logging.debug('Tests enabled: %s' % enable_tests)
logging.debug('Tests disabled: %s' % disable_tests)

mailfrom = 'root@localhost'
if httpserver:
    hostname = ''
    try:
        logging.debug('Trying to fetch real hostname from EC2')
        response = urllib2.urlopen('http://169.254.169.254/latest/meta-data/public-hostname', timeout=5)
        hostname = response.read()
        logging.debug('Fetched %s as real hostname')
    except:
        # looks like we're not in EC2 environment
        pass
    if not hostname or hostname == '':
        hostname = subprocess.check_output(['hostname', '-f'])[:-1]
    mailfrom = getpass.getuser() + '@' + hostname
    logging.debug('Will send resulting emails from ' + mailfrom)

logging.getLogger('boto').setLevel(logging.CRITICAL)

# main queue for worker threads
mainq = Queue.Queue()

# resulting dictionary
resultdic = {}
resultdic_lock = threading.Lock()

# resulting dictionary
resultdic_yaml = {}
resultdic_yaml_lock = threading.Lock()

# number of running threads
numthreads = 0
numthreads_lock = threading.Lock()

if args.data:
    # Data file was supplied
    try:
        datafd = open(args.data, 'r')
        data = yaml.load(datafd)
        datafd.close()
    except Exception, e:
        logging.error('Failed to read data file %s with error %s' % (args.data, e))
        sys.exit(1)
    add_data(data)
elif not httpserver:
    logging.error('You need to set --data or --server option!')
    sys.exit(1)

for i in range(minthreads):
    # Creating minimum amount of worker threads
    wthread = WorkerThread()
    with numthreads_lock:
        numthreads += 1
    wthread.start()

w = WatchmanThread()
w.start()

if httpserver:
    # Starting ServerThread
    s = ServerThread()
    s.start()

try:
    threads_exist = True
    while threads_exist:
        # Waiting for all threads to finish
        threads_exist = False
        for thread in threading.enumerate():
            if thread is not threading.currentThread():
                threads_exist = True
                thread.join(2)
except KeyboardInterrupt:
    print 'Got CTRL-C, exiting'
    for thread in threading.enumerate():
        if thread is not threading.currentThread() and thread.isAlive():
            try:
                thread._Thread__stop()
            except:
                print(str(thread.getName()) + ' could not be terminated')
    sys.exit(1)
